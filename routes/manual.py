"""工作手册 — Wiki 风格飞机/车辆技术参数查询.

数据来源: data/aircraft_catalog.json 和 data/vehicle_catalog.json，
由实地调研整理，与 seed.py 共享同一数据源。
保障规则由 AircraftType Python 类承载，非数据库表。
"""
import json
import os

from flask import render_template
from models.vehicle import Vehicle
from models.flight import Flight
from models.aircraft import AircraftCatalog
from models import db
from . import manual_bp

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def _load_json(filename: str):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_vehicle_specs(catalog: list) -> dict:
    """将 vehicle_catalog.json 转为 manual 页面所需的展示格式."""
    specs = {}
    for v in catalog:
        variants = v.get("variants", [])
        variant_list = ", ".join(vr["class"] for vr in variants) if variants else "通用"

        base_duration = variants[0].get("base_duration_min", "—") if variants else "—"

        # 容量/能力展示（因车型而异）
        capacity = "—"
        max_height = ""
        if v["type"] == "TOW":
            capacity = ", ".join(f'{vr["class"]} {vr["towing_force_t"]}t' for vr in variants)
        elif v["type"] == "STAIR":
            capacity = ", ".join(f'{vr["class"]} {vr["max_height_m"]}m' for vr in variants)
            max_height = f'{variants[-1]["max_height_m"]} m' if variants else ""
        elif v["type"] == "BUS":
            capacity = ", ".join(f'{vr["class"]} {vr["passenger_capacity"]}人' for vr in variants)
        elif v["type"] == "FUEL":
            capacity = ", ".join(f'{vr["class"]} {vr["capacity_l"]}L' for vr in variants)
        elif v["type"] == "BAG":
            capacity = f'{variants[0]["items_per_trip"]}件/车' if variants else "—"
        elif v["type"] == "GPU":
            capacity = f'{variants[0]["power_kva"]}kVA' if variants else "—"

        constraints = v.get("constraints", {})
        specs[v["type"]] = {
            "name": v["name"],
            "code": v["type"],
            "service_mode": "一对一（ONE_TO_ONE）" if v["service_mode"] == "ONE_TO_ONE" else "一对多（ONE_TO_MANY）",
            "variants": variant_list,
            "base_duration": f"{base_duration} 分钟",
            "crew": "1-2 人",
            "capacity": capacity,
            "max_height": max_height,
            "description": v.get("description", ""),
            "constraints": [constraints.get("note", "")] if constraints.get("note") else [],
            "compatibility": "",
        }
    return specs


def _build_aircraft_specs(catalog: list) -> dict:
    """将 aircraft_catalog.json 转为 manual 页面所需的展示格式."""
    specs = {}
    for a in catalog:
        dims = a.get("dimensions", {})
        weight = a.get("weight", {})
        perf = a.get("performance", {})
        cap = a.get("capacity", {})
        tech = a.get("technical", {})
        specs[a["type"]] = {
            "name": a["name"],
            "manufacturer": a["manufacturer"],
            "type": a["category"],
            "length": f"{dims['length_m']} m",
            "wingspan": f"{dims['wingspan_m']} m",
            "height": f"{dims['height_m']} m",
            "max_takeoff_weight": f"{weight['max_takeoff_t']} t",
            "max_landing_weight": f"{weight['max_landing_t']} t",
            "range": f"{perf['range_km']:,} km",
            "cruise_speed": perf["cruise_speed"],
            "seats": cap["seats"],
            "engine_options": f"{tech.get('engines', '—')} 台",
            "door_height_m": dims.get("door_height_m"),
            "description": a.get("description", ""),
        }
    return specs


@manual_bp.route("/manual")
def manual():
    aircraft_catalog = _load_json("aircraft_catalog.json")
    vehicle_catalog = _load_json("vehicle_catalog.json")

    vehicles = Vehicle.query.order_by(Vehicle.type, Vehicle.plate).all()

    # 车型分组
    vtype_info = {}
    for v in vehicles:
        vtype_info.setdefault(v.type, {"vehicles": [], "total": 0})
        vtype_info[v.type]["vehicles"].append(v)
        vtype_info[v.type]["total"] += 1

    # 保障规则从 AircraftType 推导，按模板兼容格式组织
    aircraft_rules = {}
    for at in AircraftCatalog.all_types():
        ac = AircraftCatalog.get(at)
        if ac:
            # 展示远机位规则（包含全部车辆类型），廊桥规则通过 note 标注差异
            tasks_remote = ac.generate_tasks(gate_has_jet_bridge=False)
            tasks_jb = ac.generate_tasks(gate_has_jet_bridge=True)
            jb_types = {t["type"] for t in tasks_jb}
            aircraft_rules[at] = []
            for t in tasks_remote:
                note = ""
                if t["type"] not in jb_types:
                    note = "仅远机位需要"
                aircraft_rules[at].append({
                    "required_vehicle_type": t["type"],
                    "quantity": t["quantity"],
                    "variant": t.get("variant", ""),
                    "note": note,
                })

    db_types = (
        db.session.query(Flight.aircraft_type)
        .distinct().filter(Flight.aircraft_type.isnot(None)).all()
    )
    known_aircraft = sorted({at[0] for at in db_types} | set(aircraft_rules.keys()))

    type_names = {
        "TOW": "牵引车", "GPU": "电源车", "STAIR": "客梯车",
        "BUS": "摆渡车", "FUEL": "加油车", "BAG": "行李车", "CLEAN": "清洁车",
    }
    status_names = {
        "IDLE": "空闲", "ASSIGNED": "已分配", "BUSY": "工作中",
        "REFUELING": "回补中", "MAINTENANCE": "维修中",
    }

    return render_template(
        "manual.html",
        vtype_info=vtype_info,
        aircraft_rules=aircraft_rules,
        known_aircraft=known_aircraft,
        aircraft_specs=_build_aircraft_specs(aircraft_catalog),
        vehicle_specs=_build_vehicle_specs(vehicle_catalog),
        type_names=type_names,
        status_names=status_names,
    )
