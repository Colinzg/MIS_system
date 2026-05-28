"""工作手册 — Wiki 风格飞机/车辆技术参数查询.

数据来源: data/aircraft_catalog.json 和 data/vehicle_catalog.json，
由实地调研整理，与 seed.py 共享同一数据源。
"""
import json
import os

from flask import render_template
from models import db
from models.vehicle import Vehicle
from models.aircraft_resource import AircraftResource
from models.flight import Flight
from . import manual_bp

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def _load_json(filename: str):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_max_height(vehicle: dict) -> str:
    """从 compatibility.rules 中提取最大升降高度范围."""
    rules = vehicle.get("compatibility", {}).get("rules", [])
    if not rules:
        return ""
    heights = sorted({r["max_height_m"] for r in rules if "max_height_m" in r})
    if not heights:
        return ""
    if len(heights) == 1:
        return f"{heights[0]} m"
    return f"{heights[0]}–{heights[-1]} m"


def _build_vehicle_specs(catalog: list) -> dict:
    """将 vehicle_catalog.json 转为 manual 页面所需的展示格式."""
    specs = {}
    for v in catalog:
        comp = v.get("compatibility", {})
        specs[v["type"]] = {
            "name": v["name"],
            "code": v["type"],
            "service_mode": "一对一（ONE_TO_ONE）" if v["service_mode"] == "ONE_TO_ONE" else "一对多（ONE_TO_MANY）",
            "base_duration": f"{v['base_duration_min']} 分钟",
            "crew": v.get("crew", "—"),
            "capacity": v.get("capacity", {}).get("label", "—"),
            "description": v.get("description", ""),
            "constraints": (
                [note] if (note := v.get("constraints", {}).get("note", "").strip()) else []
            ),
            "compatibility": comp.get("note", ""),
            "max_height": _extract_max_height(v),
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
            "engine_options": tech.get("engine_options", "—"),
            "description": a.get("description", ""),
            # 技术参数（用于推导匹配规则，展示时可选）
            "door_height_m": dims.get("door_height_m"),
            "fuel_capacity_l": tech.get("fuel_capacity_l"),
            "baggage_estimate": cap.get("baggage_estimate"),
        }
    return specs


@manual_bp.route("/manual")
def manual():
    # ── 加载调研数据 ──────────────────────────────
    aircraft_catalog = _load_json("aircraft_catalog.json")
    vehicle_catalog = _load_json("vehicle_catalog.json")

    # ── 动态数据 ──────────────────────────────────
    vehicles = Vehicle.query.order_by(Vehicle.type, Vehicle.plate).all()
    rules = AircraftResource.query.order_by(
        AircraftResource.aircraft_type, AircraftResource.required_vehicle_type
    ).all()

    # 车型分组
    vtype_info = {}
    for v in vehicles:
        vtype_info.setdefault(v.type, {"vehicles": [], "total": 0})
        vtype_info[v.type]["vehicles"].append(v)
        vtype_info[v.type]["total"] += 1

    # 机型保障规则
    aircraft_rules = {}
    for r in rules:
        aircraft_rules.setdefault(r.aircraft_type, []).append(r)

    # 所有出现的机型
    db_types = (
        db.session.query(Flight.aircraft_type)
        .distinct().filter(Flight.aircraft_type.isnot(None)).all()
    )
    known_aircraft = sorted({at[0] for at in db_types} | set(aircraft_rules.keys()))

    type_names = {"FUEL": "加油车", "BAG": "行李车", "TOW": "牵引车", "STAIR": "客梯车"}
    status_names = {
        "IDLE": "空闲", "ASSIGNED": "已分配", "CONFIRMED": "已确认",
        "BUSY": "工作中", "MAINTENANCE": "维修中",
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
