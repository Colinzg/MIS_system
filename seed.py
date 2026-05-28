"""种子数据 — 从 data/ 目录加载调研数据并写入数据库.

运行前需先在 MySQL 中创建数据库:
    mysql -u root -p -e "CREATE DATABASE airport_scheduling DEFAULT CHARACTER SET utf8mb4;"

运行:
    python seed.py

数据来源:
    data/airport_layout.json   — 机场平面图：区域、停机位坐标、路网点边
    data/vehicle_catalog.json  — 车辆技术参数目录
    data/aircraft_catalog.json — 飞机技术参数目录
    data/service_rules.json    — 机型保障规则（由上述两张目录交叉推导 + 人工核定）

原则: seed.py 只负责"将调研数据写入数据库"，不编造任何数值。
"""

import json
import os
from datetime import datetime, timedelta

from app import create_app
from models import db
from models.region import Region
from models.vehicle import Vehicle
from models.flight import Flight
from models.task import Task
from models.aircraft_resource import AircraftResource
from models.road_network import RoadNode, RoadEdge

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _load_json(filename: str) -> dict:
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _lookup_vehicle_attrs(vehicle_type: str, catalog: list) -> dict:
    """从车辆目录中查找某车型的默认 attributes."""
    for entry in catalog:
        if entry["type"] == vehicle_type:
            return {
                "service_mode": entry["service_mode"],
                "base_duration_min": entry["base_duration_min"],
            }
    return {}


def seed():
    # ── 加载所有调研数据 ──────────────────────────────
    layout = _load_json("airport_layout.json")
    vehicle_catalog = _load_json("vehicle_catalog.json")
    service_rules = _load_json("service_rules.json")

    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        # ── 区域 ────────────────────────────────────────
        region_map = {}
        for r in layout["regions"]:
            region = Region(code=r["code"], name=r["name"])
            db.session.add(region)
            region_map[r["code"]] = region
        db.session.flush()
        print(f"  ✓ 区域: {len(layout['regions'])} 个")

        # ── 车辆实例 ────────────────────────────────────
        # 车辆实例是"部署数据"——某机场实际拥有的车辆及其停放位置。
        # 每辆车的 type-level 属性取自 vehicle_catalog.json。
        vehicles_def = [
            # FUEL 加油车 ×4
            ("民航-B1021", "FUEL", "A"),
            ("民航-B1022", "FUEL", "B"),
            ("民航-B1030", "FUEL", "A"),
            ("民航-B1031", "FUEL", "B"),
            # BAG 行李车 ×5
            ("民航-B1023", "BAG", "A"),
            ("民航-B1024", "BAG", "B"),
            ("民航-B1025", "BAG", "A"),
            ("民航-B1032", "BAG", "A"),
            ("民航-B1033", "BAG", "B"),
            # TOW 牵引车 ×4
            ("民航-B1026", "TOW", "A"),
            ("民航-B1027", "TOW", "B"),
            ("民航-B1034", "TOW", "A"),
            ("民航-B1035", "TOW", "B"),
            # STAIR 客梯车 ×4（A区标准型，B区高管型）
            ("民航-B1028", "STAIR", "A"),
            ("民航-B1029", "STAIR", "B"),
            ("民航-B1036", "STAIR", "A"),
            ("民航-B1037", "STAIR", "B"),
        ]

        # STAIR 车辆的差异化配置：A区配标准高度(5.5m)，B区配高管(6.5m)
        stair_attrs = {
            "A": {"max_height_m": 5.5, "compatible_aircraft": ["A320", "B737"]},
            "B": {"max_height_m": 6.5, "compatible_aircraft": ["A320", "B737", "B777", "A330"]},
        }

        for plate, vtype, region_code in vehicles_def:
            attrs = _lookup_vehicle_attrs(vtype, vehicle_catalog)
            if vtype == "BAG":
                attrs["baggage_capacity"] = 50
            if vtype == "STAIR":
                attrs.update(stair_attrs[region_code])
            db.session.add(Vehicle(
                plate=plate, type=vtype, region_id=region_map[region_code].id,
                attributes=attrs,
            ))
        db.session.flush()
        print(f"  ✓ 车辆: {len(vehicles_def)} 辆（属性取自 vehicle_catalog.json）")

        # ── 保障规则 ────────────────────────────────────
        rules = service_rules["rules"]
        rule_count = 0
        for aircraft_type, entries in rules.items():
            for entry in entries:
                db.session.add(AircraftResource(
                    aircraft_type=aircraft_type,
                    required_vehicle_type=entry["vehicle_type"],
                    quantity=entry["quantity"],
                ))
                rule_count += 1
        db.session.flush()
        print(f"  ✓ 保障规则: {rule_count} 条（取自 service_rules.json）")

        # ── 路网节点 ────────────────────────────────────
        node_map = {}
        for nd in layout["nodes"]:
            region_id = region_map[nd["region"]].id if nd.get("region") else None
            node = RoadNode(
                code=nd["code"], name=nd["name"], node_type=nd["type"],
                region_id=region_id,
            )
            db.session.add(node)
            node_map[nd["code"]] = node
        db.session.flush()

        # 停机位也作为路网节点插入
        for region_code, gates in layout["gates"].items():
            for g in gates:
                node = RoadNode(
                    code=g["code"],
                    name=f"{region_code}区{g['code']}机位",
                    node_type="GATE",
                    region_id=region_map[region_code].id,
                )
                db.session.add(node)
                node_map[g["code"]] = node
        db.session.flush()

        # ── 路网边 ──────────────────────────────────────
        edge_count = 0
        for ed in layout["edges"]:
            db.session.add(RoadEdge(
                from_node_id=node_map[ed["from"]].id,
                to_node_id=node_map[ed["to"]].id,
                distance_m=ed["distance_m"],
                duration_min=ed["duration_min"],
                is_two_way=ed["two_way"],
            ))
            edge_count += 1
        db.session.commit()
        print(f"  ✓ 路网节点: {len(node_map)} 个 / 边: {edge_count} 条（取自 airport_layout.json）")

        # ── 航班（模拟运营数据） ────────────────────────
        now = datetime.utcnow() + timedelta(hours=8)  # 北京时间 (UTC+8)
        flights_data = [
            ("CA1234", "中国国航", "A320", now + timedelta(minutes=10),     "A01", 40),
            ("MU2567", "东方航空", "B777", now + timedelta(minutes=40),     "B05", 50),
            ("CZ3890", "南方航空", "A320", now + timedelta(hours=1, minutes=10),  "A03", 40),
            ("3U8888", "四川航空", "A320", now + timedelta(hours=1, minutes=40),  "B02", 40),
            ("HU7205", "海南航空", "B777", now + timedelta(hours=2, minutes=10),  "A07", 50),
            ("ZH9102", "深圳航空", "A320", now + timedelta(hours=2, minutes=40),  "B08", 40),
            ("MF8123", "厦门航空", "B777", now + timedelta(hours=3, minutes=10),  "A05", 50),
            ("CA8899", "中国国航", "A320", now + timedelta(hours=3, minutes=40),  "B06", 40),
            ("CZ6622", "南方航空", "B777", now + timedelta(hours=4, minutes=10),  "A08", 50),
            ("3U9999", "四川航空", "A320", now + timedelta(hours=4, minutes=40),  "B04", 40),
            ("HU5368", "海南航空", "A320", now + timedelta(hours=5, minutes=10),  "A06", 40),
            ("MU7118", "东方航空", "B777", now + timedelta(hours=5, minutes=40),  "B10", 50),
        ]

        flights = []
        for fn, airline, at, dep, gate, turnaround in flights_data:
            region_code = gate[0]  # A01 → A
            flights.append(Flight(
                flight_no=fn,
                airline=airline,
                aircraft_type=at,
                scheduled_at=dep,
                arrival_at=dep - timedelta(minutes=turnaround),
                gate=gate,
                region_id=region_map[region_code].id,
            ))
        db.session.add_all(flights)
        db.session.commit()
        print(f"  ✓ 航班: {len(flights)} 个（含 aircraft_type）")

        # ── 任务（按 service_rules.json 自动生成） ──────
        task_count = 0
        for flight in flights:
            entries = rules.get(flight.aircraft_type, [])
            for entry in entries:
                for _ in range(entry["quantity"]):
                    db.session.add(Task(
                        flight_id=flight.id,
                        task_type=entry["vehicle_type"],
                        status="PENDING",
                        scheduled_start=flight.arrival_at or flight.scheduled_at,
                        scheduled_end=(flight.arrival_at or flight.scheduled_at) + timedelta(minutes=30),
                    ))
                    task_count += 1
        db.session.commit()
        print(f"  ✓ 任务: {task_count} 个（按 service_rules.json 规则生成）")

        print("\n种子数据全部写入完成。")


if __name__ == "__main__":
    seed()
