"""种子数据 — 从 data/ 目录加载参考数据并写入数据库.

架构:
  JSON 文件         — 数据交换格式（团队协作、版本管理）
  MySQL 数据库       — 唯一运行时数据源，所有模块只读写数据库

运行前需先在 MySQL 中创建数据库:
    mysql -u root -p -e "CREATE DATABASE airport_scheduling DEFAULT CHARACTER SET utf8mb4;"

运行:
    python seed.py
"""
import json
import os
from datetime import datetime, timedelta

from sqlalchemy import text

from app import create_app
from models import db
from models.region import Region
from models.gate import Gate
from models.vehicle import VehicleModel, VehicleInfo, VehicleStatus
from models.flight import Flight
from models.road_network import RoadNode, RoadEdge
from services.task_generator import TaskGenerator

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _load_json(filename: str) -> dict:
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def seed():
    layout = _load_json("airport_physical.json")
    vehicle_models = _load_json("vehicle_models.json")
    inventory = _load_json("vehicle_inventory.json")

    app = create_app()
    with app.app_context():
        # 手动关闭外键检查后删除全部旧表，再重新建表
        # 因为 db.drop_all() 内部使用独立连接，session 级的
        # FOREIGN_KEY_CHECKS 对其不生效，改用 raw SQL。
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        db.session.commit()
        tables = [row[0] for row in db.session.execute(text("SHOW TABLES")).fetchall()]
        for t in tables:
            db.session.execute(text(f"DROP TABLE IF EXISTS `{t}`"))
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        db.session.commit()
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
                )
                db.session.add(gate)
                gate_map[g["code"]] = gate
        db.session.flush()
        jetbridge_count = sum(1 for g in gate_map.values() if g.has_jet_bridge)
        print(f"  OK 停机位: {len(gate_map)} 个（廊桥 {jetbridge_count} / 远机位 {len(gate_map) - jetbridge_count}）")

        # ── 车辆型号 — 从 vehicle_models.json 导入 ────────
        model_count = 0
        for entry in vehicle_models:
            for m in entry.get("models", []):
                vm = VehicleModel(
                    vehicle_type=entry["vehicle_type"],
                    brand_model=m["brand_model"],
                    manufacturer=m.get("manufacturer"),
                    size_class=m.get("size_class"),
                    specs={k: v for k, v in m.items() if k not in (
                        "brand_model", "manufacturer", "size_class",
                        "compatible_aircraft", "base_duration_min",
                    )},
                    compatible_aircraft=m.get("compatible_aircraft"),
                    base_duration_min=m.get("base_duration_min"),
                )
                db.session.add(vm)
                model_count += 1
        db.session.flush()
        print(f"  OK 车辆型号: {model_count} 种（{len(vehicle_models)} 个类型）")

        # ── 车辆 — 从 vehicle_inventory.json 导入 ────────
        type_count = {}
        for v in inventory:
            info = VehicleInfo(
                plate_number=v["plate_number"],
                vehicle_type=v["vehicle_type"],
                brand_model=v["brand_model"],
                size_class=v.get("size_class"),
                region=v.get("region", "A"),
                purchase_date=datetime.strptime(v["purchase_date"], "%Y-%m-%d").date()
                if v.get("purchase_date") else None,
                asset_tag=v.get("asset_tag"),
                remark=v.get("remark"),
            )
            db.session.add(info)
            status = VehicleStatus(
                plate_number=v["plate_number"],
                current_status="IDLE",
            )
            db.session.add(status)
            type_count[v["vehicle_type"]] = type_count.get(v["vehicle_type"], 0) + 1
        db.session.flush()
        summary = ", ".join(f"{t}{c}台" for t, c in sorted(type_count.items()))
        print(f"  OK 车辆: {len(inventory)} 台（{summary}）")

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
            # (航班号, 航空公司, 机型,  计划起飞(now+偏移),    停机位, 过站分钟, 加油)
            # 车辆任务总耗时 ~8-10min，scheduled_at 留足余量（≥10min）
            # 每 5-8 分钟一班，A区 B区 交替，廊桥远机位混合
            ("CA1234", "中国国航", "A320", now + timedelta(minutes=10),     "A01", 20, True),
            ("MU2567", "东方航空", "B777", now + timedelta(minutes=16),     "B05", 25, True),
            ("CZ3890", "南方航空", "A320", now + timedelta(minutes=22),     "B01", 20, False),
            ("HU7205", "海南航空", "A330", now + timedelta(minutes=28),     "A03", 25, True),
            ("ZH9102", "深圳航空", "B737", now + timedelta(minutes=34),     "B06", 20, False),
            ("MF8123", "厦门航空", "A330", now + timedelta(minutes=40),     "B03", 25, True),
            ("CA8899", "中国国航", "A320", now + timedelta(minutes=46),     "B08", 20, True),
            ("CZ6622", "南方航空", "B777", now + timedelta(minutes=52),     "A04", 25, False),
            ("MU6677", "东方航空", "B737", now + timedelta(minutes=58),     "A07", 20, False),
            ("HU5368", "海南航空", "A330", now + timedelta(minutes=64),     "B05", 25, True),
            ("ZH8001", "深圳航空", "B737", now + timedelta(minutes=70),     "B02", 20, False),
            ("CA5566", "中国国航", "A320", now + timedelta(minutes=76),     "A08", 20, True),
        ]

        flights = []
        for fn, airline, at, dep, gate_code, turnaround, needs_fuel in flights_data:
            region_code = gate_code[0]  # A01 → A
            f = Flight(
                flight_no=fn,
                airline=airline,
                aircraft_type=at,
                needs_fuel=needs_fuel,
                scheduled_at=dep,
                arrival_at=dep - timedelta(minutes=turnaround),
                gate_id=gate_map[gate_code].id,
                region_id=region_map[region_code].id,
            )
            db.session.add(f)
            flights.append(f)
        db.session.commit()

        fuel_count = sum(1 for f in flights if f.needs_fuel)
        print(f"  OK 航班: {len(flights)} 个（加油 {fuel_count} / 不加油 {len(flights) - fuel_count}，4种机型，廊桥+远机位混合）")

        # ── 任务（由 AircraftType.generate_tasks() 生成）──
        total_tasks = 0
        for flight in flights:
            result = TaskGenerator.generate_for_flight(flight.id)
            total_tasks += result["tasks_created"]
        print(f"  OK 任务: {total_tasks} 个（按机型规则自动生成，含依赖链）")

        # ── 统计摘要 ─────────────────────────────────────
        print(f"\n{'='*50}")
        print(f"种子数据写入完成。")
        print(f"  区域: {len(layout['regions'])} | 停机位: {len(gate_map)} | 车辆型号: {model_count} | 车辆: {len(inventory)}")
        print(f"  航班: {len(flights)} | 任务: {total_tasks}")
        print(f"{'='*50}")


if __name__ == "__main__":
    seed()
