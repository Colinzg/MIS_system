"""调度核心逻辑 — 为航班自动分配地面服务车辆.

调度优先级规则（简化）:
  1. 区域优先 — 优先选择与航班在同一区域的车辆
  2. 空闲优先 — 同区域内选状态为 IDLE 的车辆
  3. 跨区域兜底 — 若本区域无可用车辆，从其他区域调度

使用示例:
    scheduler = Scheduler()
    result = scheduler.schedule_for_flight(flight_id=1)
"""
from models import db
from models.vehicle import Vehicle
from models.task import Task
from models.flight import Flight


class Scheduler:
    """调度器：封装车辆分配算法."""

    # 每种航班保障任务所需的标准时长（分钟）
    DURATIONS = {
        "FUEL": 15,
        "BAG": 20,
        "TOW": 10,
        "STAIR": 10,
    }

    def schedule_for_flight(self, flight_id: int) -> dict:
        """为指定航班未分配车辆的 PENDING 任务分配车辆.

        对航班下所有仍为 PENDING 且无车辆的任务，
        按区域优先 → 空闲优先的顺序分配车辆。

        Args:
            flight_id: 航班 ID

        Returns:
            dict: {
                "flight_id": ...,
                "tasks": [{"task_type": ..., "vehicle_id": ..., "status": ...}, ...],
                "errors": [...]
            }

        Raises:
            ValueError: 航班不存在
        """
        flight = db.session.get(Flight, flight_id)
        if not flight:
            raise ValueError(f"Flight {flight_id} not found")

        pending_tasks = Task.query.filter_by(
            flight_id=flight_id, status="PENDING", vehicle_id=None,
        ).all()

        result = {"flight_id": flight_id, "tasks": [], "errors": []}

        if not pending_tasks:
            result["errors"].append("no pending tasks to assign")
            return result

        for task in pending_tasks:
            vehicle = self._select_vehicle(task.task_type, flight.region_id)
            if vehicle:
                task.vehicle_id = vehicle.id
                task.status = "IN_PROGRESS"
                vehicle.status = "BUSY"
                result["tasks"].append({
                    "task_type": task.task_type,
                    "vehicle_id": vehicle.id,
                    "status": "IN_PROGRESS",
                })
            else:
                result["errors"].append(
                    f"{task.task_type}: no available vehicle"
                )

        db.session.commit()
        return result

    def _select_vehicle(self, task_type: str, region_id: int):
        """按优先级选车：同区域 IDLE → 异区域 IDLE → None."""
        vehicle = Vehicle.query.filter_by(
            type=task_type, status="IDLE", region_id=region_id,
        ).first()
        if vehicle:
            return vehicle
        return Vehicle.query.filter_by(
            type=task_type, status="IDLE",
        ).first()
