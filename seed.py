"""种子数据 — 初始化数据库并插入模拟数据.

运行方式:
    1. 先手动在 MySQL 中创建数据库:
       mysql -u root -p -e "CREATE DATABASE airport_scheduling DEFAULT CHARACTER SET utf8mb4;"
    2. 运行本脚本:
       python seed.py

将会清空现有数据并插入:
  - 2 个区域（A / B），各含 10 个停机位（A01-A10 / B01-B10）
  - 停车场编码: A-1（A 区）、B-1（B 区）
  - 9 辆车（每种车型 2-3 辆），停放在指定停车场
  - 6 个模拟航班，分配在各停机位
  - 各航班根据 aircraft_type 自动生成保障任务
  - A320 / B777 的 AircraftResource 规则
  - 机场路网节点与边
"""

from datetime import datetime, timedelta
from app import create_app
from models import db
from models.region import Region
from models.vehicle import Vehicle
from models.flight import Flight
from models.task import Task
from models.aircraft_resource import AircraftResource
from models.road_network import RoadNode, RoadEdge


def seed():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        # ── 区域 ────────────────────────────────────────
        regions = [
            Region(code="A", name="A 区"),
            Region(code="B", name="B 区"),
        ]
        db.session.add_all(regions)
        db.session.flush()

        # ── 车辆（停放于各区域停车场，停车场编码 A-1 / B-1） ──
        vehicles = [
            Vehicle(plate="民航-B1021", type="FUEL", region_id=regions[0].id,
                    attributes={"service_mode": "ONE_TO_ONE", "base_duration_min": 20}),
            Vehicle(plate="民航-B1022", type="FUEL", region_id=regions[1].id,
                    attributes={"service_mode": "ONE_TO_ONE", "base_duration_min": 20}),
            Vehicle(plate="民航-B1023", type="BAG", region_id=regions[0].id,
                    attributes={"service_mode": "ONE_TO_MANY", "baggage_capacity": 50, "base_duration_min": 15}),
            Vehicle(plate="民航-B1024", type="BAG", region_id=regions[1].id,
                    attributes={"service_mode": "ONE_TO_MANY", "baggage_capacity": 50, "base_duration_min": 15}),
            Vehicle(plate="民航-B1025", type="BAG", region_id=regions[0].id,
                    attributes={"service_mode": "ONE_TO_MANY", "baggage_capacity": 50, "base_duration_min": 15}),
            Vehicle(plate="民航-B1026", type="TOW", region_id=regions[0].id,
                    attributes={"service_mode": "ONE_TO_ONE", "base_duration_min": 10}),
            Vehicle(plate="民航-B1027", type="TOW", region_id=regions[1].id,
                    attributes={"service_mode": "ONE_TO_ONE", "base_duration_min": 10}),
            Vehicle(plate="民航-B1028", type="STAIR", region_id=regions[0].id,
                    attributes={"service_mode": "ONE_TO_ONE", "max_height_m": 5.5,
                                "compatible_aircraft": ["A320", "B737"], "base_duration_min": 5}),
            Vehicle(plate="民航-B1029", type="STAIR", region_id=regions[1].id,
                    attributes={"service_mode": "ONE_TO_ONE", "max_height_m": 6.5,
                                "compatible_aircraft": ["A320", "B737", "B777"], "base_duration_min": 5}),
        ]
        db.session.add_all(vehicles)
        db.session.flush()

        # ── AircraftResource 规则 ──────────────────────
        rules = [
            # A320 保障规则
            AircraftResource(aircraft_type="A320", required_vehicle_type="FUEL", quantity=1),
            AircraftResource(aircraft_type="A320", required_vehicle_type="BAG", quantity=2),
            AircraftResource(aircraft_type="A320", required_vehicle_type="TOW", quantity=1),
            AircraftResource(aircraft_type="A320", required_vehicle_type="STAIR", quantity=1),
            # B777 保障规则
            AircraftResource(aircraft_type="B777", required_vehicle_type="FUEL", quantity=1),
            AircraftResource(aircraft_type="B777", required_vehicle_type="BAG", quantity=3),
            AircraftResource(aircraft_type="B777", required_vehicle_type="TOW", quantity=1),
            AircraftResource(aircraft_type="B777", required_vehicle_type="STAIR", quantity=2),
        ]
        db.session.add_all(rules)
        db.session.flush()

        # ── 路网节点与边 ────────────────────────────────
        nodes = [
            RoadNode(code="N01", name="A区入口", node_type="INTERSECTION", region_id=regions[0].id),
            RoadNode(code="N02", name="A区出口", node_type="INTERSECTION", region_id=regions[0].id),
            RoadNode(code="N03", name="B区入口", node_type="INTERSECTION", region_id=regions[1].id),
            RoadNode(code="N04", name="B区出口", node_type="INTERSECTION", region_id=regions[1].id),
            RoadNode(code="FUEL_STATION", name="加油站", node_type="SERVICE_STATION"),
        ]
        db.session.add_all(nodes)
        db.session.flush()

        edges = [
            RoadEdge(from_node_id=nodes[0].id, to_node_id=nodes[1].id,
                     distance_m=500, duration_min=2, is_two_way=True),
            RoadEdge(from_node_id=nodes[1].id, to_node_id=nodes[2].id,
                     distance_m=1200, duration_min=5, is_two_way=True),
            RoadEdge(from_node_id=nodes[2].id, to_node_id=nodes[3].id,
                     distance_m=500, duration_min=2, is_two_way=True),
            RoadEdge(from_node_id=nodes[1].id, to_node_id=nodes[4].id,
                     distance_m=300, duration_min=1, is_two_way=True),
            RoadEdge(from_node_id=nodes[3].id, to_node_id=nodes[4].id,
                     distance_m=300, duration_min=1, is_two_way=True),
        ]
        db.session.add_all(edges)
        db.session.flush()

        # ── 航班 ────
        now = datetime.utcnow()
        base = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        flights = [
            Flight(flight_no="CA1234", airline="中国国航", aircraft_type="A320",
                   scheduled_at=base, gate="A01", region_id=regions[0].id),
            Flight(flight_no="MU2567", airline="东方航空", aircraft_type="B777",
                   scheduled_at=base + timedelta(hours=1), gate="B05", region_id=regions[1].id),
            Flight(flight_no="CZ3890", airline="南方航空", aircraft_type="A320",
                   scheduled_at=base + timedelta(hours=1, minutes=30), gate="A03", region_id=regions[0].id),
            Flight(flight_no="3U8888", airline="四川航空", aircraft_type="A320",
                   scheduled_at=base + timedelta(hours=2), gate="B02", region_id=regions[1].id),
            Flight(flight_no="HU7205", airline="海南航空", aircraft_type="B777",
                   scheduled_at=base + timedelta(hours=3), gate="A07", region_id=regions[0].id),
            Flight(flight_no="ZH9102", airline="深圳航空", aircraft_type="A320",
                   scheduled_at=base + timedelta(hours=4), gate="B08", region_id=regions[1].id),
        ]
        db.session.add_all(flights)
        db.session.commit()

        # ── 任务（根据规则自动生成） ────────────────────
        task_count = 0
        for flight in flights:
            flight_rules = AircraftResource.query.filter_by(
                aircraft_type=flight.aircraft_type
            ).all()
            for rule in flight_rules:
                for _ in range(rule.quantity):
                    db.session.add(Task(
                        flight_id=flight.id,
                        task_type=rule.required_vehicle_type,
                        status="PENDING",
                        scheduled_start=flight.scheduled_at,
                        scheduled_end=flight.scheduled_at + timedelta(minutes=30),
                    ))
                    task_count += 1

        db.session.commit()

        # ── 统计输出 ────────────────────────────────────
        gates_a = [f"A{i:02d}" for i in range(1, 9)]
        gates_b = [f"B{i:02d}" for i in range(1, 9)]
        print("✓ 种子数据插入成功")
        print(f"  - 区域: {len(regions)} 个（A / B）")
        print(f"  - 停机位: A 区 {len(gates_a)} 个, B 区 {len(gates_b)} 个")
        print(f"  - 停车场: A-1, B-1")
        print(f"  - 车辆: {len(vehicles)} 辆（含 attributes）")
        print(f"  - 保障规则: {len(rules)} 条")
        print(f"  - 路网节点: {len(nodes)} 个 / 边: {len(edges)} 条")
        print(f"  - 航班: {len(flights)} 个（含 aircraft_type）")
        print(f"  - 任务: {task_count} 个（按机型规则生成）")


if __name__ == "__main__":
    seed()
