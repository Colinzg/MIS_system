"""种子数据 — 初始化数据库并插入模拟数据.

运行方式:
    1. 先手动在 MySQL 中创建数据库:
       mysql -u root -p -e "CREATE DATABASE airport_scheduling DEFAULT CHARACTER SET utf8mb4;"
    2. 运行本脚本:
       python seed.py

将会清空现有数据并插入:
  - 3 个区域（A01 / B02 / C03）
  - 9 辆车（每种车型 2-3 辆）
  - 6 个模拟航班
  - 每个航班自动生成 4 个 PENDING 任务
"""

from datetime import datetime, timedelta
from app import create_app
from models import db
from models.region import Region
from models.vehicle import Vehicle
from models.flight import Flight
from models.task import Task


def seed():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        # ── 区域 ────────────────────────────────────────
        regions = [
            Region(code="A01", name="1号航站楼东侧"),
            Region(code="B02", name="2号航站楼西侧"),
            Region(code="C03", name="货运区"),
        ]
        db.session.add_all(regions)
        db.session.flush()

        # ── 车辆（每种 2-3 辆，共 9 辆） ────────────────
        vehicles = [
            Vehicle(plate="京A-FUEL01", type="FUEL", region_id=regions[0].id),
            Vehicle(plate="京A-FUEL02", type="FUEL", region_id=regions[1].id),
            Vehicle(plate="京A-BAG01",  type="BAG",  region_id=regions[0].id),
            Vehicle(plate="京A-BAG02",  type="BAG",  region_id=regions[1].id),
            Vehicle(plate="京A-BAG03",  type="BAG",  region_id=regions[2].id),
            Vehicle(plate="京A-TOW01",  type="TOW",  region_id=regions[0].id),
            Vehicle(plate="京A-TOW02",  type="TOW",  region_id=regions[2].id),
            Vehicle(plate="京A-STAIR01", type="STAIR", region_id=regions[1].id),
            Vehicle(plate="京A-STAIR02", type="STAIR", region_id=regions[2].id),
        ]
        db.session.add_all(vehicles)
        db.session.flush()

        # ── 航班（6 个） ────────────────────────────────
        now = datetime.utcnow()
        base = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        flights = [
            Flight(flight_no="CA1234", airline="中国国航", scheduled_at=base,
                   gate="A12", region_id=regions[0].id),
            Flight(flight_no="MU2567", airline="东方航空", scheduled_at=base + timedelta(hours=1),
                   gate="B05", region_id=regions[1].id),
            Flight(flight_no="CZ3890", airline="南方航空", scheduled_at=base + timedelta(hours=1, minutes=30),
                   gate="C03", region_id=regions[2].id),
            Flight(flight_no="3U8888", airline="四川航空", scheduled_at=base + timedelta(hours=2),
                   gate="A08", region_id=regions[0].id),
            Flight(flight_no="HU7205", airline="海南航空", scheduled_at=base + timedelta(hours=3),
                   gate="B12", region_id=regions[1].id),
            Flight(flight_no="ZH9102", airline="深圳航空", scheduled_at=base + timedelta(hours=4),
                   gate="C07", region_id=regions[2].id),
        ]
        db.session.add_all(flights)
        db.session.flush()

        # ── 任务（每航班 4 个 PENDING 任务） ────────────
        task_types = ["FUEL", "BAG", "TOW", "STAIR"]
        for flight in flights:
            for ttype in task_types:
                db.session.add(
                    Task(
                        flight_id=flight.id,
                        task_type=ttype,
                        status="PENDING",
                        scheduled_start=flight.scheduled_at,
                        scheduled_end=flight.scheduled_at
                        + timedelta(minutes=30),
                    )
                )

        db.session.commit()
        print("✓ 种子数据插入成功")
        print(f"  - 区域: {len(regions)} 个")
        print(f"  - 车辆: {len(vehicles)} 辆")
        print(f"  - 航班: {len(flights)} 个")
        print(f"  - 任务: {len(flights) * len(task_types)} 个")


if __name__ == "__main__":
    seed()
