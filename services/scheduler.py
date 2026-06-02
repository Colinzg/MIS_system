"""调度规划子系统 — 为航班保障任务分配最合适的车辆.

职责 (对应 UC 矩阵):
  - 读取: vehicle_models 表、vehicle_info 表、vehicle_status 表、地面服务任务
  - 创建: 调度分配结果 (任务-车辆绑定)

调度约束优先级:
  1. 车型匹配 — task_type 与 vehicle_type 一致
  2. 机型兼容 — vehicle_models.compatible_aircraft 包含目标机型
  3. 区域优先 — 同区域空闲车辆优先
  4. 任务依赖 — 前置任务未完成时暂不分配
"""
import json
import os
from models import db
from models.vehicle import VehicleInfo, VehicleStatus
from models.task import Task
from models.flight import Flight

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _load_vehicle_models() -> list:
    path = os.path.join(DATA_DIR, "vehicle_models.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_model_compatible_aircraft(brand_model: str) -> list:
    """从 vehicle_models.json 查询指定型号的兼容机型列表."""
    catalog = _load_vehicle_models()
    for entry in catalog:
        for m in entry.get("models", []):
            if m["brand_model"] == brand_model:
                return m.get("compatible_aircraft", [])
    return []


class Scheduler:
    """调度器：封装多约束车辆分配算法."""

    def schedule_for_flight(self, flight_id: int) -> dict:
        """为指定航班的 PENDING 任务按约束链分配车辆."""
        flight = db.session.get(Flight, flight_id)
        if not flight:
            raise ValueError(f"Flight {flight_id} not found")

        pending_tasks = Task.query.filter_by(
            flight_id=flight_id, status="PENDING", plate_number=None,
        ).all()

        result = {"flight_id": flight_id, "tasks": [], "errors": []}
        if not pending_tasks:
            result["errors"].append("no pending tasks to assign")
            return result

        ordered = self._topological_sort(pending_tasks)

        for task in ordered:
            if task.depends_on and not self._dependency_met(task.depends_on):
                result["errors"].append(
                    f"{task.task_type}(#{task.id}): dependency #{task.depends_on} not completed"
                )
                continue

            # TOW 特殊约束：必须等所有其他任务完成才能分配
            if task.task_type == "TOW" and not self._all_other_tasks_completed(task):
                result["errors"].append(
                    f"TOW(#{task.id}): waiting for all other tasks to complete"
                )
                continue

            plate = self._select_vehicle(task, flight)
            if plate:
                task.plate_number = plate
                task.status = "IN_PROGRESS"
                vstat = db.session.query(VehicleStatus).filter_by(plate_number=plate).first()
                if vstat:
                    vstat.current_status = "ASSIGNED"
                vinfo = db.session.get(VehicleInfo, plate)
                result["tasks"].append({
                    "task_type": task.task_type,
                    "plate_number": plate,
                    "brand_model": vinfo.brand_model if vinfo else "",
                    "status": "IN_PROGRESS",
                })
            else:
                result["errors"].append(
                    f"{task.task_type}: no compatible vehicle available"
                )

        db.session.commit()
        return result

    def _select_vehicle(self, task: Task, flight: Flight) -> str | None:
        """按约束链选车，返回 plate_number.

        1. 车型匹配 task_type
        2. 机型兼容（通过 vehicle_models.compatible_aircraft）
        3. 区域优先
        """
        # 同车型且空闲的车辆
        candidates = db.session.query(VehicleInfo, VehicleStatus).join(
            VehicleStatus, VehicleInfo.plate_number == VehicleStatus.plate_number
        ).filter(
            VehicleInfo.vehicle_type == task.task_type,
            VehicleStatus.current_status == "IDLE",
        ).all()

        if not candidates:
            return None

        # 机型兼容过滤
        compatible = []
        for vinfo, vstat in candidates:
            compat_list = _get_model_compatible_aircraft(vinfo.brand_model)
            if not compat_list or flight.aircraft_type in compat_list:
                compatible.append((vinfo, vstat))

        if not compatible:
            return None

        # 区域优先
        for vinfo, vstat in compatible:
            if vinfo.region == flight.region.code:
                return vinfo.plate_number

        return compatible[0][0].plate_number

    @staticmethod
    def _dependency_met(depends_on_task_id: int) -> bool:
        task = db.session.get(Task, depends_on_task_id)
        return task is not None and task.status == "COMPLETED"

    @staticmethod
    def _all_other_tasks_completed(task: Task) -> bool:
        """检查同一航班下除本任务外所有任务是否都已完成（TOW 专用）."""
        other_tasks = Task.query.filter(
            Task.flight_id == task.flight_id,
            Task.id != task.id,
        ).all()
        return all(t.status == "COMPLETED" for t in other_tasks)

    @staticmethod
    def _topological_sort(tasks: list) -> list:
        sorted_tasks = []
        remaining = set(tasks)
        while remaining:
            ready = [
                t for t in remaining
                if t.depends_on is None
                or Scheduler._dependency_met(t.depends_on)
            ]
            if not ready:
                sorted_tasks.extend(remaining)
                break
            sorted_tasks.extend(ready)
            remaining -= set(ready)
        return sorted_tasks
