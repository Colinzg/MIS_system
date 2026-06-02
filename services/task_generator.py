"""任务生成子系统 — 根据航班机型和停机位属性创建地面服务任务.

职责 (对应 UC 矩阵):
  - 读取: 航班信息、机位属性、机型领域知识 (AircraftType)
  - 创建: 地面服务任务 (Task)，含依赖链

规则来源: AircraftType.generate_tasks() — 由 aircraft_catalog.json 技术参数推导，
不是数据库配置表。这是"业务建模"的核心体现。
"""
from datetime import datetime, timedelta
from models import db
from models.flight import Flight
from models.gate import Gate
from models.task import Task
from models.aircraft import AircraftCatalog


class TaskGenerator:
    """根据机型保障规则批量生成任务，并设置依赖链."""

    @staticmethod
    def generate_for_flight(flight_id: int) -> dict:
        """为指定航班生成全部保障任务，含依赖关系.

        流程:
          1. 读取 Flight → 获取 aircraft_type, gate_id
          2. 读取 Gate → 获取 has_jet_bridge
          3. AircraftCatalog.get(type) → AircraftType 实例
          4. aircraft.generate_tasks(has_jet_bridge) → 任务规格列表
          5. 两遍创建: 先建 Task 记录拿到 ID，再设置 depends_on

        Returns:
            {"flight_id": ..., "tasks_created": int, "errors": [str]}
        """
        flight = db.session.get(Flight, flight_id)
        if not flight:
            raise ValueError(f"Flight {flight_id} not found")
        if not flight.aircraft_type:
            raise ValueError(f"Flight {flight_id} has no aircraft_type set")

        aircraft = AircraftCatalog.get(flight.aircraft_type)
        if not aircraft:
            return {
                "flight_id": flight_id,
                "tasks_created": 0,
                "errors": [f"unknown aircraft_type: {flight.aircraft_type}"],
            }

        gate = db.session.get(Gate, flight.gate_id) if flight.gate_id else None
        has_jet_bridge = gate.has_jet_bridge if gate else True

        # needs_fuel 由航班属性决定，当前默认 False
        needs_fuel = getattr(flight, 'needs_fuel', False)
        task_specs = aircraft.generate_tasks(has_jet_bridge, needs_fuel)

        # Pass 1: 创建 Task 记录，记录 task_type → task.id 映射
        type_to_ids: dict[str, int] = {}
        created_tasks = []
        for spec in task_specs:
            task = Task(
                flight_id=flight.id,
                task_type=spec["type"],
                status="PENDING",
                scheduled_start=flight.arrival_at or flight.scheduled_at,
            )
            db.session.add(task)
            db.session.flush()  # 获取 task.id
            created_tasks.append(task)
            type_to_ids[spec["type"]] = task.id

        # Pass 2: 设置 depends_on
        for spec in task_specs:
            dep_type = spec.get("depends_on_type")
            if dep_type and dep_type in type_to_ids:
                task_id = type_to_ids[spec["type"]]
                t = db.session.get(Task, task_id)
                if t:
                    t.depends_on = type_to_ids[dep_type]

        db.session.commit()
        return {
            "flight_id": flight_id,
            "tasks_created": len(created_tasks),
            "errors": [],
        }

    @staticmethod
    def generate_for_upcoming(hours: int = 3) -> dict:
        """为未来指定小时内所有尚无任务的航班生成保障任务."""
        now = datetime.utcnow() + timedelta(hours=8)
        deadline = now + timedelta(hours=hours)

        flights = Flight.query.filter(
            Flight.scheduled_at >= now,
            Flight.scheduled_at <= deadline,
        ).order_by(Flight.scheduled_at).all()

        processed = 0
        total_created = 0
        errors = []

        for flight in flights:
            existing = Task.query.filter_by(
                flight_id=flight.id, status="PENDING"
            ).count()
            if existing > 0:
                continue

            try:
                result = TaskGenerator.generate_for_flight(flight.id)
                total_created += result["tasks_created"]
                processed += 1
                errors.extend(result["errors"])
            except ValueError as e:
                errors.append(str(e))

        return {
            "flights_processed": processed,
            "tasks_created": total_created,
            "errors": errors,
        }
