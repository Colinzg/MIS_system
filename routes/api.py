"""态势图数据 API — 为机场地图提供实时位置数据.

停机位和停车场坐标从 data/airport_display.json 加载（纯显示数据），
物理属性（廊桥、路网等）由 data/airport_physical.json 提供，两者分离。
"""
import json
import os
from datetime import datetime, timedelta
from flask import jsonify, request
from models.vehicle import VehicleInfo, VehicleStatus
from models.flight import Flight
from models.task import Task
from models.comm_log import CommunicationLog
from models import db
from . import api_bp

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def _load_display():
    path = os.path.join(DATA_DIR, "airport_display.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_gate_coords():
    """从 airport_display.json 加载停机位显示坐标."""
    display = _load_display()
    coords = {}
    for code, pos in display["gates"].items():
        region = code[0]  # A01 → A
        coords[code] = {"x": pos["x"], "y": pos["y"], "region": region}
    return coords


def _build_parking_coords():
    """从 airport_display.json 加载停车场显示坐标."""
    display = _load_display()
    coords = {}
    for code, pa in display["parking_areas"].items():
        coords[pa["region"]] = {"x": pa["x"], "y": pa["y"], "label": code}
    return coords


GATE_COORDS = _build_gate_coords()
PARKING_COORDS = _build_parking_coords()

VEHICLE_TYPE_ICONS = {
    "TOW": "\U0001f69c", "GPU": "\U0001f50c", "STAIR": "\U0001fa9c", "BUS": "\U0001f68c",
    "FUEL": "⛽", "BAG": "\U0001f9f3",
}

TASK_TYPE_NAMES = {
    "TOW": "牵引", "GPU": "电源", "STAIR": "客梯", "BUS": "摆渡",
    "FUEL": "加油", "BAG": "行李",
}


@api_bp.route("/api/map-data")
def map_data():
    """返回态势图所需的全部数据（仅显示已入位航班）."""
    now = datetime.utcnow() + timedelta(hours=8)  # 北京时间
    flights = Flight.query.filter(
        Flight.arrival_at.isnot(None),
        Flight.arrival_at <= now,
    ).order_by(Flight.scheduled_at).all()

    # 查询车辆：JOIN vehicle_info + vehicle_status
    vehicles = db.session.query(VehicleInfo, VehicleStatus).join(
        VehicleStatus, VehicleInfo.plate_number == VehicleStatus.plate_number
    ).order_by(VehicleInfo.vehicle_type, VehicleInfo.plate_number).all()

    active_tasks = Task.query.filter(
        Task.status == "IN_PROGRESS", Task.plate_number.isnot(None)
    ).all()
    vehicle_to_flight = {t.plate_number: t.flight_id for t in active_tasks}

    # 航班→服务车辆映射
    flight_to_vehicles = {}
    for t in active_tasks:
        if t.flight_id is None:
            continue
        flight_to_vehicles.setdefault(t.flight_id, [])
        vinfo = db.session.get(VehicleInfo, t.plate_number)
        if vinfo:
            flight_to_vehicles[t.flight_id].append({
                "plate": t.plate_number,
                "type_icon": VEHICLE_TYPE_ICONS.get(vinfo.vehicle_type, ""),
                "type": vinfo.vehicle_type,
            })

    flights_data = []
    for f in flights:
        gate_code = f.gate.code if f.gate else None
        gate = GATE_COORDS.get(gate_code) if gate_code else None
        pos = {"x": gate["x"], "y": gate["y"]} if gate else None
        flights_data.append({
            "id": f.id,
            "flight_no": f.flight_no,
            "airline": f.airline,
            "aircraft_type": f.aircraft_type,
            "gate": gate_code,
            "region": f.region.code if f.region else None,
            "status": f.status,
            "position": pos,
            "assigned_vehicles": flight_to_vehicles.get(f.id, []),
        })

    _park_offsets = {}
    vehicles_data = []
    for vinfo, vstat in vehicles:
        parking = PARKING_COORDS.get(vinfo.region, PARKING_COORDS["A"])
        assigned_flight_id = vehicle_to_flight.get(vinfo.plate_number)

        if assigned_flight_id:
            flight = db.session.get(Flight, assigned_flight_id)
            if flight and flight.gate:
                gate = GATE_COORDS.get(flight.gate.code)
                pos = {"x": gate["x"], "y": gate["y"] - 28} if gate else {"x": parking["x"], "y": parking["y"]}
            else:
                pos = {"x": parking["x"], "y": parking["y"]}
        else:
            key = f"{vinfo.region}_{vinfo.vehicle_type}"
            offset = _park_offsets.get(key, 0)
            _park_offsets[key] = offset + 1
            pos = {
                "x": parking["x"] - 22 + (offset % 3) * 15,
                "y": parking["y"] - 6 + (offset // 3) * 18,
            }

        vehicles_data.append({
            "id": vstat.id,
            "plate_number": vinfo.plate_number,
            "type": vinfo.vehicle_type,
            "type_label": VEHICLE_TYPE_ICONS.get(vinfo.vehicle_type, vinfo.vehicle_type),
            "status": vstat.current_status,
            "region": vinfo.region,
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
    plate_number = data.get("plate_number")

    task = db.session.get(Task, task_id)
    vstat = db.session.query(VehicleStatus).filter_by(plate_number=plate_number).first()
    vinfo = db.session.get(VehicleInfo, plate_number) if plate_number else None

    if not task or not vstat:
        return jsonify({"ok": False, "error": "任务或车辆不存在"}), 404
    if task.status != "PENDING":
        return jsonify({"ok": False, "error": "任务状态不是 PENDING，无法分配"}), 400
    if not vinfo or task.task_type != vinfo.vehicle_type:
        return jsonify({"ok": False, "error": f"车型不匹配：需要 {task.task_type}"}), 400
    if vstat.current_status != "IDLE":
        return jsonify({"ok": False, "error": f"车辆当前状态为 {vstat.current_status}，不可分配"}), 400

    task.plate_number = plate_number
    task.status = "IN_PROGRESS"
    vstat.current_status = "ASSIGNED"
    db.session.commit()

    # 自动向车辆发送任务通知
    gate = task.flight.gate.code if task.flight and task.flight.gate else "--"
    flight_no = task.flight.flight_no if task.flight else "--"
    notif = CommunicationLog(
        plate_number=plate_number, sender="DISPATCH",
        content=f"【新任务】{flight_no} {gate} 机位，{TASK_TYPE_NAMES.get(task.task_type, task.task_type)}任务，请立即前往。",
        msg_type="TASK",
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({"ok": True, "task_id": task.id, "plate_number": plate_number})


@api_bp.route("/api/auto-assign", methods=["POST"])
def auto_assign():
    """自动为所有 PENDING 任务分配车辆."""
    from services.scheduler import Scheduler

    flights = Flight.query.filter(
        Flight.id.in_(db.session.query(Task.flight_id).filter(
            Task.status == "PENDING", Task.plate_number.is_(None)
        ))
    ).all()

    scheduler = Scheduler()
    results = []
    total_errors = 0
    for flight in flights:
        r = scheduler.schedule_for_flight(flight.id)
        results.append({
            "flight_id": flight.id,
            "flight_no": flight.flight_no,
            "tasks": r["tasks"],
            "errors": r["errors"],
        })
        total_errors += len(r["errors"])

    return jsonify({
        "ok": True,
        "assigned": sum(len(r["tasks"]) for r in results),
        "flights": len(results),
        "errors": total_errors,
        "details": results,
    })


@api_bp.route("/api/vehicle/confirm-task", methods=["POST"])
def confirm_task():
    """车辆确认接收任务（ASSIGNED → BUSY）."""
    data = request.get_json()
    plate_number = data.get("plate_number")
    vstat = db.session.query(VehicleStatus).filter_by(plate_number=plate_number).first()
    if not vstat:
        return jsonify({"ok": False, "error": "车辆不存在"}), 404
    if vstat.current_status != "ASSIGNED":
        return jsonify({"ok": False, "error": f"车辆状态为 {vstat.current_status}，不是已分配状态"}), 400

    vstat.current_status = "BUSY"
    notif = CommunicationLog(
        plate_number=plate_number, sender="VEHICLE",
        content="已确认任务，准备前往。",
        msg_type="STATUS",
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({"ok": True, "vehicle_status": "BUSY"})


@api_bp.route("/api/vehicle/start-work", methods=["POST"])
def start_work():
    """车辆开始执行任务（CONFIRMED → BUSY）."""
    data = request.get_json()
    plate_number = data.get("plate_number")
    vstat = db.session.query(VehicleStatus).filter_by(plate_number=plate_number).first()
    if not vstat:
        return jsonify({"ok": False, "error": "车辆不存在"}), 404
    if vstat.current_status != "ASSIGNED":
        return jsonify({"ok": False, "error": f"车辆状态为 {vstat.current_status}，不是已分配状态"}), 400

    vstat.current_status = "BUSY"
    db.session.commit()

    return jsonify({"ok": True, "vehicle_status": "BUSY"})


@api_bp.route("/api/comm/send", methods=["POST"])
def comm_send():
    """发送通讯消息（调度中心 → 车辆 / 车辆 → 调度中心）."""
    data = request.get_json()
    plate_number = data.get("plate_number")
    sender = data.get("sender", "").upper()
    content = (data.get("content") or "").strip()
    msg_type = data.get("msg_type", "TEXT").upper()

    if not plate_number or not content:
        return jsonify({"ok": False, "error": "缺少 plate_number 或 content"}), 400
    if sender not in ("DISPATCH", "VEHICLE"):
        return jsonify({"ok": False, "error": "sender 必须是 DISPATCH 或 VEHICLE"}), 400
    if not db.session.get(VehicleInfo, plate_number):
        return jsonify({"ok": False, "error": "车辆不存在"}), 404

    log = CommunicationLog(
        plate_number=plate_number, sender=sender,
        content=content, msg_type=msg_type,
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({"ok": True, "message": log.to_dict()})


@api_bp.route("/api/comm/poll")
def comm_poll():
    """轮询获取未读消息（车载终端用），支持按车辆过滤."""
    plate_number = request.args.get("plate_number")
    since = request.args.get("since")

    q = CommunicationLog.query.order_by(CommunicationLog.created_at.asc())

    if plate_number:
        q = q.filter_by(plate_number=plate_number)
    if since:
        q = q.filter(CommunicationLog.created_at > since)

    logs = q.all()
    for log in logs:
        if log.sender == "DISPATCH" and not log.read:
            log.read = True
    db.session.commit()

    return jsonify({"ok": True, "messages": [l.to_dict() for l in logs]})


@api_bp.route("/api/comm/history")
def comm_history():
    """获取与指定车辆的完整通讯记录（调度面板用）."""
    plate_number = request.args.get("plate_number")
    since = request.args.get("since")

    q = CommunicationLog.query
    if plate_number:
        q = q.filter_by(plate_number=plate_number)
    if since:
        q = q.filter(CommunicationLog.created_at > since).order_by(CommunicationLog.created_at.asc())
    else:
        q = q.order_by(CommunicationLog.created_at.desc()).limit(50)

    logs = q.all()

    if plate_number:
        unread = CommunicationLog.query.filter_by(
            plate_number=plate_number, sender="VEHICLE", read=False
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
        CommunicationLog.plate_number,
        func.count(CommunicationLog.id).label("cnt"),
    ).filter(
        CommunicationLog.sender == "VEHICLE",
        CommunicationLog.read == False,
    ).group_by(CommunicationLog.plate_number).all()

    unread_map = {r.plate_number: r.cnt for r in rows}

    result = {}
    vehicles = db.session.query(VehicleInfo, VehicleStatus).join(
        VehicleStatus, VehicleInfo.plate_number == VehicleStatus.plate_number
    ).all()
    for vinfo, vstat in vehicles:
        result[vstat.id] = {
            "plate_number": vinfo.plate_number,
            "type": vinfo.vehicle_type,
            "icon": VEHICLE_TYPE_ICONS.get(vinfo.vehicle_type, "\U0001f69b"),
            "status": vstat.current_status,
            "unread": unread_map.get(vinfo.plate_number, 0),
        }
    return jsonify({"ok": True, "unread": result})


@api_bp.route("/api/vehicle/task/<plate_number>")
def vehicle_active_task(plate_number):
    """返回车辆当前进行中的任务（车载终端轮询用）."""
    vstat = db.session.query(VehicleStatus).filter_by(plate_number=plate_number).first()
    vehicle_status = vstat.current_status if vstat else None

    task = Task.query.filter_by(
        plate_number=plate_number, status="IN_PROGRESS"
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
            "task_type_name": TASK_TYPE_NAMES.get(task.task_type, task.task_type),
            "flight_no": flight.flight_no if flight else None,
            "gate": flight.gate.code if flight and flight.gate else None,
            "scheduled_start": task.scheduled_start.strftime("%H:%M") if task.scheduled_start else None,
        },
    })
