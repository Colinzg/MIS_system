"""任务生成子系统 — 根据航班信息和保障规则创建地面服务任务.

职责 (对应 UC 矩阵):
  - 读取: 航班信息、保障规则 (AircraftResource)
  - 创建: 地面服务任务 (Task)

数据流向: 任务生成 → 调度规划 (输出待分配任务列表)
"""
from models import db
from models.flight import Flight
from models.aircraft_resource import AircraftResource
from models.task import Task


class TaskGenerator:
    """根据航班机型匹配 AircraftResource 规则，批量生成保障任务."""

    @staticmethod
    def generate_for_flight(flight_id: int) -> dict:
        """为指定航班生成所有 PENDING 保障任务.

        读取航班的 aircraft_type → 查询 AircraftResource 规则表 →
        为每条规则创建对应 Task.

        Args:
            flight_id: 航班 ID

        Returns:
            {"flight_id": ..., "tasks_created": int, "errors": [str]}

        Raises:
            ValueError: 航班不存在或缺少机型信息
        """
        flight = db.session.get(Flight, flight_id)
        if not flight:
            raise ValueError(f"Flight {flight_id} not found")
        if not flight.aircraft_type:
            raise ValueError(f"Flight {flight_id} has no aircraft_type set")

        rules = AircraftResource.query.filter_by(
            aircraft_type=flight.aircraft_type
        ).all()
        if not rules:
            return {
                "flight_id": flight_id,
                "tasks_created": 0,
                "errors": [f"no AircraftResource rules for {flight.aircraft_type}"],
            }

        created = 0
        errors = []
        for rule in rules:
            for _ in range(rule.quantity):
                task = Task(
                    flight_id=flight.id,
                    task_type=rule.required_vehicle_type,
                    status="PENDING",
                    scheduled_start=flight.scheduled_at,
                )
                db.session.add(task)
                created += 1

        db.session.commit()
        return {"flight_id": flight_id, "tasks_created": created, "errors": errors}
