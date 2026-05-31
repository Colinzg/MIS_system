"""种子数据 — 从 data/ 目录加载调研数据并写入数据库.

三层架构:
  Layer 1: data/*.json      — 领域知识库（飞机/车辆技术参数、机场布局）
  Layer 2: models/aircraft.py — 保障规则（Python 类，由技术参数推导）
  Layer 3: MySQL 运行时表     — 航班/车辆/任务/机位/区域

运行前需先在 MySQL 中创建数据库:
    mysql -u root -p -e "CREATE DATABASE airport_scheduling DEFAULT CHARACTER SET utf8mb4;"

运行:
    python seed.py

原则: seed.py 只负责"将调研数据写入数据库"，规则推导由 AircraftType 类完成。
"""
import json
import os
from datetime import datetime, timedelta

from app import create_app
from models import db
from models.region import Region
from models.gate import Gate
from models.vehicle import Vehicle
from models.flight import Flight
from models.road_network import RoadNode, RoadEdge
from services.task_generator import TaskGenerator

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _load_json(filename: str) -> dict:
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def seed():
    layout = _load_json("airport_layout.json")

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
        print(f"  OK 区域: {len(layout['regions'])} 个")

        # ── 停机位 ──────────────────────────────────────
        gate_map = {}
        for region_code, gates in layout["gates"].items():
            for g in gates:
                gate = Gate(
                    code=g["code"],
                    region_id=region_map[region_code].id,
                    has_jet_bridge=g["has_jet_bridge"],
                    x=g.get("x"),
                    y=g.get("y"),
                )
                db.session.add(gate)
                gate_map[g["code"]] = gate
        db.session.flush()
        jetbridge_count = sum(1 for g in gate_map.values() if g.has_jet_bridge)
        print(f"  OK 停机位: {len(gate_map)} 个（廊桥 {jetbridge_count} / 远机位 {len(gate_map) - jetbridge_count}）")

        # ── 车辆实例 ────────────────────────────────────
        # variant 指向 vehicle_catalog.json 中 variants[].class
        vehicles_def = [
            # TOW 牵引车 — 三种等级
            ("民航-B2001", "TOW", "标准型",  "A"),
            ("民航-B2002", "TOW", "标准型",  "B"),
            ("民航-B2003", "TOW", "重型",    "A"),
            ("民航-B2004", "TOW", "超重型",  "A"),

            # GPU 电源车 — 通用型
            ("民航-B2005", "GPU", "通用型", "A"),
            ("民航-B2006", "GPU", "通用型", "A"),
            ("民航-B2007", "GPU", "通用型", "B"),
            ("民航-B2008", "GPU", "通用型", "B"),

            # STAIR 客梯车 — 三种高度等级（仅远机位需要，但车辆要预先部署）
            ("民航-B2009", "STAIR", "标准型",  "A"),
            ("民航-B2010", "STAIR", "标准型",  "B"),
            ("民航-B2011", "STAIR", "高管型",  "A"),
            ("民航-B2012", "STAIR", "超高管型","A"),

            # BUS 摆渡车 — 两种容量（仅远机位需要）
            ("民航-B2013", "BUS", "小型", "A"),
            ("民航-B2014", "BUS", "小型", "B"),
            ("民航-B2015", "BUS", "大型", "A"),
            ("民航-B2016", "BUS", "大型", "B"),

            # FUEL 加油车 — 两种容量
            ("民航-B2017", "FUEL", "标准型",   "A"),
            ("民航-B2018", "FUEL", "标准型",   "B"),
            ("民航-B2019", "FUEL", "大容量型", "A"),
            ("民航-B2020", "FUEL", "大容量型", "B"),

            # BAG 行李车 — 通用型（可串飞多航班）
            ("民航-B2021", "BAG", "通用型", "A"),
            ("民航-B2022", "BAG", "通用型", "A"),
            ("民航-B2023", "BAG", "通用型", "B"),
            ("民航-B2024", "BAG", "通用型", "B"),

            # CLEAN 清洁车 — 通用型
            ("民航-B2025", "CLEAN", "通用型", "A"),
            ("民航-B2026", "CLEAN", "通用型", "A"),
            ("民航-B2027", "CLEAN", "通用型", "B"),
        ]

        for plate, vtype, variant, region_code in vehicles_def:
            db.session.add(Vehicle(
                plate=plate, type=vtype, variant=variant,
                region_id=region_map[region_code].id,
            ))
        db.session.flush()
        print(f"  OK 车辆: {len(vehicles_def)} 辆（7 种车型，多等级部署）")

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
        print(f"  OK 路网节点: {len(node_map)} 个 / 边: {edge_count} 条")

        # ── 航班（模拟运营数据） ────────────────────────
        now = datetime.utcnow() + timedelta(hours=8)  # 北京时间
        flights_data = [
            # (航班号, 航空公司, 机型,  计划起飞,         停机位, 过站分钟)
            ("CA1234", "中国国航", "A320", now + timedelta(minutes=10),     "A01", 40),   # 廊桥
            ("MU2567", "东方航空", "B777", now + timedelta(minutes=40),     "A06", 50),   # 远机位
            ("CZ3890", "南方航空", "A320", now + timedelta(hours=1, minutes=10),  "B01", 40),   # 廊桥
            ("3U8888", "四川航空", "A380", now + timedelta(hours=1, minutes=40),  "A08", 60),   # 远机位, 超大型
            ("HU7205", "海南航空", "B787", now + timedelta(hours=2, minutes=10),  "A03", 45),   # 廊桥
            ("ZH9102", "深圳航空", "B737", now + timedelta(hours=2, minutes=40),  "B06", 40),   # 远机位
            ("MF8123", "厦门航空", "A330", now + timedelta(hours=3, minutes=10),  "B03", 45),   # 廊桥
            ("CA8899", "中国国航", "A320", now + timedelta(hours=3, minutes=40),  "B08", 40),   # 远机位
            ("CZ6622", "南方航空", "B777", now + timedelta(hours=4, minutes=10),  "A04", 50),   # 廊桥
            ("3U9999", "四川航空", "B737", now + timedelta(hours=4, minutes=40),  "A07", 40),   # 远机位
            ("HU5368", "海南航空", "A330", now + timedelta(hours=5, minutes=10),  "B05", 45),   # 远机位
            ("MU7118", "东方航空", "B787", now + timedelta(hours=5, minutes=40),  "B02", 45),   # 廊桥
        ]

        flights = []
        for fn, airline, at, dep, gate_code, turnaround in flights_data:
            region_code = gate_code[0]  # A01 → A
            f = Flight(
                flight_no=fn,
                airline=airline,
                aircraft_type=at,
                scheduled_at=dep,
                arrival_at=dep - timedelta(minutes=turnaround),
                gate_id=gate_map[gate_code].id,
                region_id=region_map[region_code].id,
            )
            db.session.add(f)
            flights.append(f)
        db.session.commit()
        print(f"  OK 航班: {len(flights)} 个（覆盖 6 种机型，廊桥+远机位混合）")

        # ── 任务（由 AircraftType.generate_tasks() 生成）──
        total_tasks = 0
        for flight in flights:
            result = TaskGenerator.generate_for_flight(flight.id)
            total_tasks += result["tasks_created"]
        print(f"  OK 任务: {total_tasks} 个（按机型规则自动生成，含依赖链）")

        # ── 统计摘要 ─────────────────────────────────────
        print(f"\n{'='*50}")
        print(f"种子数据写入完成。")
        print(f"  区域: {len(layout['regions'])} | 停机位: {len(gate_map)} | 车辆: {len(vehicles_def)}")
        print(f"  航班: {len(flights)} | 任务: {total_tasks}")
        print(f"{'='*50}")


if __name__ == "__main__":
    seed()
