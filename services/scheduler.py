"""调度规划子系统 — 为航班保障任务分配最合适的车辆.

职责 (对应 UC 矩阵):
  - 读取: 保障规则、地面服务任务、车辆状态
  - 创建: 调度分配结果 (任务-车辆绑定)

调度约束优先级:
  1. 机型适配 — 车辆 attributes 中 compatible_aircraft 是否包含目标机型
  2. 服务模式 — ONE_TO_ONE 车辆同一时间只能分配一个任务
  3. 区域匹配 — 优先分配同区域车辆，减少空驶
  4. 任务依赖 — 前置任务未完成时暂不分配
  5. 满载约束 — 需回补的车辆在回补完成前不可分配
"""
from datetime import datetime
from models import db
from models.vehicle import Vehicle
from models.task import Task
from models.flight import Flight
from services.vehicle_manager import VehicleManager


class Scheduler:
    """调度器：封装多约束车辆分配算法."""

    # 每种任务的标准作业时长（分钟），后续可移至 AircraftResource 或配置
    DURATIONS = {
        "FUEL": 15,
        "BAG": 20,
        "TOW": 10,
        "STAIR": 10,
        "GPU": 15,
        "ACU": 15,
        "BUS": 10,
    }

    def schedule_for_flight(self, flight_id: int) -> dict:
        """为指定航班的 PENDING 任务按约束链分配车辆.

        Args:
            flight_id: 航班 ID

        Returns:
            {"flight_id": int, "tasks": [dict], "errors": [str]}
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

        # 按依赖顺序排序：无依赖的任务优先分配
        ordered = self._topological_sort(pending_tasks)

        for task in ordered:
            # 检查前置依赖是否已完成
            if task.depends_on and not self._dependency_met(task.depends_on):
                result["errors"].append(
                    f"{task.task_type}(#{task.id}): dependency #{task.depends_on} not completed"
                )
                continue

            vehicle = self._select_vehicle(
                task.task_type, flight.region_id, flight.aircraft_type
            )
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

    def _select_vehicle(self, task_type: str, region_id: int,
                        aircraft_type: str = None):
        """按约束链选车: 同区域 IDLE + 机型适配 → 异区域 IDLE + 机型适配 → None."""
        candidates = Vehicle.query.filter_by(
            type=task_type, status="IDLE",
        ).all()

        # 过滤机型适配
        if aircraft_type:
            candidates = [v for v in candidates
                          if self._check_compatibility(v, aircraft_type)]

        # 区域优先
        for v in candidates:
            if v.region_id == region_id:
                return v

        # 跨区兜底
        return candidates[0] if candidates else None

    @staticmethod
    def _check_compatibility(vehicle: Vehicle, aircraft_type: str) -> bool:
        """检查车辆机型适配.

        若 vehicle.attributes 中未定义 compatible_aircraft，默认兼容所有机型。
        """
        if not vehicle.attributes:
            return True
        compatible = vehicle.attributes.get("compatible_aircraft")
        if compatible is None:
            return True
        return aircraft_type in compatible

    @staticmethod
    def _dependency_met(depends_on_task_id: int) -> bool:
        """检查前置任务是否已完成."""
        task = db.session.get(Task, depends_on_task_id)
        return task is not None and task.status == "COMPLETED"

    @staticmethod
    def _topological_sort(tasks: list) -> list:
        """按任务依赖关系拓扑排序，无依赖的任务排前面."""
        sorted_tasks = []
        remaining = set(tasks)
        while remaining:
            # 找到所有当前无未满足依赖的任务
            ready = [t for t in remaining
                     if t.depends_on is None
                     or db.session.get(Task, t.depends_on) is None
                     or db.session.get(Task, t.depends_on).status == "COMPLETED"]
            if not ready:
                # 有环或依赖不可达，直接追加剩余任务
                sorted_tasks.extend(remaining)
                break
            sorted_tasks.extend(ready)
            remaining -= set(ready)
        return sorted_tasks
