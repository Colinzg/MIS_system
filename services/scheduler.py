"""调度规划子系统 — 为航班保障任务分配最合适的车辆.

职责 (对应 UC 矩阵):
  - 读取: 保障规则 (vehicle_catalog.json)、地面服务任务、车辆状态
  - 创建: 调度分配结果 (任务-车辆绑定)

调度约束优先级:
  1. 车型匹配 — task_type 一致
  2. 等级匹配 — task.required_variant 与 vehicle.variant 一致
  3. 机型适配 — 车辆 variant 的技术参数满足目标机型要求
  4. 区域优先 — 同区域空闲车辆优先，减少空驶
  5. 任务依赖 — 前置任务未完成时暂不分配
  6. 容量约束 — 需回补的车辆在回补完成前不可分配
"""
import json
import os
from models import db
from models.vehicle import Vehicle
from models.task import Task
from models.flight import Flight
from models.aircraft import AircraftCatalog

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _load_vehicle_catalog() -> list:
    path = os.path.join(DATA_DIR, "vehicle_catalog.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _find_variant_spec(vehicle_type: str, variant_class: str) -> dict:
    """在 vehicle_catalog.json 中查找指定车型等级的规格."""
    catalog = _load_vehicle_catalog()
    for entry in catalog:
        if entry["type"] == vehicle_type:
            for v in entry.get("variants", []):
                if v["class"] == variant_class:
                    return v
    return {}


class Scheduler:
    """调度器：封装多约束车辆分配算法."""

    def schedule_for_flight(self, flight_id: int) -> dict:
        """为指定航班的 PENDING 任务按约束链分配车辆."""
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

            vehicle = self._select_vehicle(task, flight)
            if vehicle:
                task.vehicle_id = vehicle.id
                task.status = "IN_PROGRESS"
                vehicle.status = "ASSIGNED"
                result["tasks"].append({
                    "task_type": task.task_type,
                    "vehicle_id": vehicle.id,
                    "vehicle_plate": vehicle.plate,
                    "variant": vehicle.variant,
                    "status": "IN_PROGRESS",
                })
            else:
                result["errors"].append(
                    f"{task.task_type}(variant={task.required_variant}): no available vehicle"
                )

        db.session.commit()
        return result

    def _select_vehicle(self, task: Task, flight: Flight):
        """按约束链选车.

        1. 车型 + 等级匹配的 IDLE 车辆
        2. 区域优先（同区域 > 跨区）
        3. 机型适配验证
        """
        query = Vehicle.query.filter_by(type=task.task_type, status="IDLE")

        # 等级匹配
        if task.required_variant:
            query = query.filter_by(variant=task.required_variant)

        candidates = query.all()

        # 机型适配验证
        if flight.aircraft_type:
            aircraft = AircraftCatalog.get(flight.aircraft_type)
            if aircraft:
                candidates = [
                    v for v in candidates
                    if self._check_variant_compatibility(v, aircraft)
                ]

        # 区域优先
        for v in candidates:
            if v.region_id == flight.region_id:
                return v

        return candidates[0] if candidates else None

    @staticmethod
    def _check_variant_compatibility(vehicle: Vehicle, aircraft) -> bool:
        """验证车辆 variant 的技术参数是否满足该机型要求.

        从 vehicle_catalog.json 读取 variant 的技术约束，与 aircraft 参数比对。
        """
        variant_spec = _find_variant_spec(vehicle.type, vehicle.variant)
        if not variant_spec:
            return True  # 查不到规格默认放行

        # TOW: 检查 compatible_max_aircraft_t
        if vehicle.type == "TOW":
            max_aircraft_t = variant_spec.get("compatible_max_aircraft_t")
            if max_aircraft_t and aircraft.max_takeoff_t > max_aircraft_t:
                return False

        # STAIR: 检查 max_height_m
        if vehicle.type == "STAIR":
            max_height = variant_spec.get("compatible_door_height_max_m")
            if max_height and aircraft.door_height_m > max_height:
                return False

        return True

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
