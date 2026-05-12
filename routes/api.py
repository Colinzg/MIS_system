"""态势图数据 API — 为机场地图提供实时位置数据."""
from datetime import datetime, timedelta
from flask import jsonify, request
from models.vehicle import Vehicle
from models.flight import Flight
from models.task import Task
from models.comm_log import CommunicationLog
from models import db
from . import api_bp

# 停机位坐标 — A区左，B区右，中间为停车场+塔台
GATE_COORDS = {}
for i in range(1, 9):
    GATE_COORDS[f"A{i:02d}"] = {"x": 30 + (i - 1) * 52, "y": 102, "region": "A"}
for i in range(1, 9):
    GATE_COORDS[f"B{i:02d}"] = {"x": 606 + (i - 1) * 52, "y": 102, "region": "B"}

# 停车场坐标 — 塔台两侧
PARKING_COORDS = {
    "A": {"x": 445, "y": 35, "label": "A-1"},
    "B": {"x": 575, "y": 35, "label": "B-1"},
}

VEHICLE_TYPE_ICONS = {
    "FUEL": "⛽", "BAG": "🧳", "TOW": "🚜", "STAIR": "🪜",
}


@api_bp.route("/api/map-data")
def map_data():
    """返回态势图所需的全部数据（仅显示已入位航班）."""
    now = datetime.utcnow() + timedelta(hours=8)  # 北京时间
    flights = Flight.query.filter(
        Flight.arrival_at.isnot(None),
        Flight.arrival_at <= now,
    ).order_by(Flight.scheduled_at).all()
    vehicles = Vehicle.query.order_by(Vehicle.type, Vehicle.plate).all()

    active_tasks = Task.query.filter(
        Task.status == "IN_PROGRESS", Task.vehicle_id.isnot(None)
    ).all()
    vehicle_to_flight = {t.vehicle_id: t.flight_id for t in active_tasks}

    # 航班→服务车辆映射
    flight_to_vehicles = {}
    for t in active_tasks:
        if t.flight_id is None:
            continue
        flight_to_vehicles.setdefault(t.flight_id, [])
        v = Vehicle.query.get(t.vehicle_id)
        if v:
            flight_to_vehicles[t.flight_id].append({
                "plate": v.plate,
                "type_icon": VEHICLE_TYPE_ICONS.get(v.type, ""),
                "type": v.type,
            })

    flights_data = []
    for f in flights:
        gate = GATE_COORDS.get(f.gate) if f.gate else None
        pos = {"x": gate["x"], "y": gate["y"]} if gate else None
        flights_data.append({
            "id": f.id,
            "flight_no": f.flight_no,
            "airline": f.airline,
            "aircraft_type": f.aircraft_type,
            "gate": f.gate,
            "region": f.region.code if f.region else None,
            "status": f.status,
            "position": pos,
            "assigned_vehicles": flight_to_vehicles.get(f.id, []),
        })

    _park_offsets = {}
    vehicles_data = []
    for v in vehicles:
        region_code = v.region.code if v.region else "A"
        parking = PARKING_COORDS.get(region_code, PARKING_COORDS["A"])
        assigned_flight_id = vehicle_to_flight.get(v.id)

        if assigned_flight_id:
            flight = Flight.query.get(assigned_flight_id)
            if flight and flight.gate:
                gate = GATE_COORDS.get(flight.gate)
                pos = {"x": gate["x"], "y": gate["y"] - 28} if gate else {"x": parking["x"], "y": parking["y"]}
            else:
                pos = {"x": parking["x"], "y": parking["y"]}
        else:
            key = f"{region_code}_{v.type}"
            offset = _park_offsets.get(key, 0)
            _park_offsets[key] = offset + 1
            pos = {
                "x": parking["x"] - 22 + (offset % 3) * 15,
                "y": parking["y"] - 6 + (offset // 3) * 18,
            }

        vehicles_data.append({
            "id": v.id,
            "plate": v.plate,
            "type": v.type,
            "type_label": VEHICLE_TYPE_ICONS.get(v.type, v.type),
            "status": v.status,
            "region": region_code,
            "position": pos,
        })

    return jsonify({
        "flights": flights_data,
        "vehicles": vehicles_data,
        "gates": [{"code": code, **coord} for code, coord in GATE_COORDS.items()],
        "parking_areas": [
            {"code": data["label"], "region": reg, "x": data["x"], "y": data["y"]}
            for reg, data in PARKING_COORDS.items()
        ],
    })


@api_bp.route("/api/assign-task", methods=["POST"])
def assign_task():
    """手动分配车辆到任务."""
    data = request.get_json()
    task_id = data.get("task_id")
    vehicle_id = data.get("vehicle_id")

    task = Task.query.get(task_id)
    vehicle = Vehicle.query.get(vehicle_id)

    if not task or not vehicle:
        return jsonify({"ok": False, "error": "任务或车辆不存在"}), 404
    if task.status != "PENDING":
        return jsonify({"ok": False, "error": "任务状态不是 PENDING，无法分配"}), 400
    if task.task_type != vehicle.type:
        return jsonify({"ok": False, "error": f"车型不匹配：需要 {task.task_type}，拖拽的是 {vehicle.type}"}), 400
    if vehicle.status != "IDLE":
        return jsonify({"ok": False, "error": f"车辆当前状态为 {vehicle.status}，不可分配"}), 400

    task.vehicle_id = vehicle.id
    task.status = "IN_PROGRESS"
    vehicle.status = "ASSIGNED"
    db.session.commit()

    # 自动向车辆发送任务通知
    from models.comm_log import CommunicationLog
    from services.task_generator import TaskGenerator
    task_type_name = {"FUEL": "加油", "BAG": "行李", "TOW": "牵引", "STAIR": "客梯"}.get(task.task_type, task.task_type)
    gate = task.flight.gate if task.flight else "--"
    flight_no = task.flight.flight_no if task.flight else "--"
    notif = CommunicationLog(
        vehicle_id=vehicle.id, sender="DISPATCH",
        content=f"【新任务】{flight_no} {gate} 机位，{task_type_name}任务，请立即前往。",
        msg_type="TASK",
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({"ok": True, "task_id": task.id, "vehicle_id": vehicle.id})


@api_bp.route("/api/vehicle/confirm-task", methods=["POST"])
def confirm_task():
    """车辆确认接收任务（ASSIGNED → BUSY）."""
    data = request.get_json()
    vehicle_id = data.get("vehicle_id")
    vehicle = db.session.get(Vehicle, vehicle_id)
    if not vehicle:
        return jsonify({"ok": False, "error": "车辆不存在"}), 404
    if vehicle.status != "ASSIGNED":
        return jsonify({"ok": False, "error": f"车辆状态为 {vehicle.status}，不是已分配状态"}), 400

    vehicle.status = "CONFIRMED"
    notif = CommunicationLog(
        vehicle_id=vehicle.id, sender="VEHICLE",
        content="已确认任务，准备前往。",
        msg_type="STATUS",
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({"ok": True, "vehicle_status": "CONFIRMED"})


@api_bp.route("/api/vehicle/start-work", methods=["POST"])
def start_work():
    """车辆开始执行任务（CONFIRMED → BUSY）."""
    data = request.get_json()
    vehicle_id = data.get("vehicle_id")
    vehicle = db.session.get(Vehicle, vehicle_id)
    if not vehicle:
        return jsonify({"ok": False, "error": "车辆不存在"}), 404
    if vehicle.status != "CONFIRMED":
        return jsonify({"ok": False, "error": f"车辆状态为 {vehicle.status}，不是已确认状态"}), 400

    vehicle.status = "BUSY"
    db.session.commit()

    return jsonify({"ok": True, "vehicle_status": "BUSY"})


@api_bp.route("/api/comm/send", methods=["POST"])
def comm_send():
    """发送通讯消息（调度中心 → 车辆 / 车辆 → 调度中心）."""
    data = request.get_json()
    vehicle_id = data.get("vehicle_id")
    sender = data.get("sender", "").upper()
    content = (data.get("content") or "").strip()
    msg_type = data.get("msg_type", "TEXT").upper()

    if not vehicle_id or not content:
        return jsonify({"ok": False, "error": "缺少 vehicle_id 或 content"}), 400
    if sender not in ("DISPATCH", "VEHICLE"):
        return jsonify({"ok": False, "error": "sender 必须是 DISPATCH 或 VEHICLE"}), 400
    vehicle = db.session.get(Vehicle, vehicle_id)
    if not vehicle:
        return jsonify({"ok": False, "error": "车辆不存在"}), 404

    log = CommunicationLog(
        vehicle_id=vehicle_id, sender=sender,
        content=content, msg_type=msg_type,
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({"ok": True, "message": log.to_dict()})


@api_bp.route("/api/comm/poll")
def comm_poll():
    """轮询获取未读消息（车载终端用），支持按车辆过滤."""
    vehicle_id = request.args.get("vehicle_id", type=int)
    since = request.args.get("since")

    q = CommunicationLog.query.order_by(CommunicationLog.created_at.asc())

    if vehicle_id:
        q = q.filter_by(vehicle_id=vehicle_id)
    if since:
        q = q.filter(CommunicationLog.created_at > since)

    # 车辆侧轮询时标记调度消息为已读
    logs = q.all()
    for log in logs:
        if log.sender == "DISPATCH" and not log.read:
            log.read = True
    db.session.commit()

    return jsonify({"ok": True, "messages": [l.to_dict() for l in logs]})


@api_bp.route("/api/comm/history")
def comm_history():
    """获取与指定车辆的完整通讯记录（调度面板用）."""
    vehicle_id = request.args.get("vehicle_id", type=int)
    since = request.args.get("since")

    q = CommunicationLog.query
    if vehicle_id:
        q = q.filter_by(vehicle_id=vehicle_id)
    if since:
        q = q.filter(CommunicationLog.created_at > since).order_by(CommunicationLog.created_at.asc())
    else:
        q = q.order_by(CommunicationLog.created_at.desc()).limit(50)

    logs = q.all()

    # 调度面板加载时标记车辆消息为已读
    if vehicle_id:
        unread = CommunicationLog.query.filter_by(
            vehicle_id=vehicle_id, sender="VEHICLE", read=False
        ).all()
        for log in unread:
            log.read = True
        db.session.commit()

    if since:
        messages = [l.to_dict() for l in logs]
    else:
        messages = [l.to_dict() for l in reversed(logs)]

    return jsonify({"ok": True, "messages": messages})


@api_bp.route("/api/comm/unread")
def comm_unread():
    """获取调度中心未读消息数量（按车辆分组）."""
    from sqlalchemy import func

    rows = db.session.query(
        CommunicationLog.vehicle_id,
        func.count(CommunicationLog.id).label("cnt"),
    ).filter(
        CommunicationLog.sender == "VEHICLE",
        CommunicationLog.read == False,
    ).group_by(CommunicationLog.vehicle_id).all()

    unread_map = {r.vehicle_id: r.cnt for r in rows}

    result = {}
    for v in Vehicle.query.all():
        result[v.id] = {
            "plate": v.plate,
            "unread": unread_map.get(v.id, 0),
        }
    return jsonify({"ok": True, "unread": result})


@api_bp.route("/api/vehicle/task/<int:vehicle_id>")
def vehicle_active_task(vehicle_id):
    """返回车辆当前进行中的任务（车载终端轮询用）."""
    vehicle = db.session.get(Vehicle, vehicle_id)
    vehicle_status = vehicle.status if vehicle else None

    task = Task.query.filter_by(
        vehicle_id=vehicle_id, status="IN_PROGRESS"
    ).first()
    if not task:
        return jsonify({"ok": True, "task": None, "vehicle_status": vehicle_status})

    flight = task.flight
    return jsonify({
        "ok": True,
        "vehicle_status": vehicle_status,
        "task": {
            "id": task.id,
            "task_type": task.task_type,
            "task_type_name": {"FUEL": "加油", "BAG": "行李", "TOW": "牵引", "STAIR": "客梯"}.get(task.task_type, task.task_type),
            "flight_no": flight.flight_no if flight else None,
            "gate": flight.gate if flight else None,
            "scheduled_start": task.scheduled_start.strftime("%H:%M") if task.scheduled_start else None,
        },
    })
