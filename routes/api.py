"""态势图数据 API — 为机场地图提供实时位置数据."""
from flask import jsonify, request
from models.vehicle import Vehicle
from models.flight import Flight
from models.task import Task
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
    """返回态势图所需的全部数据."""
    flights = Flight.query.order_by(Flight.scheduled_at).all()
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
    vehicle.status = "BUSY"
    db.session.commit()

    return jsonify({"ok": True, "task_id": task.id, "vehicle_id": vehicle.id})
