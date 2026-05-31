"""车辆管理子系统 — 维护车辆基础信息与实时状态.

职责 (对应 UC 矩阵):
  - 读取: 车辆基础信息、地面服务任务
  - 创建: 车辆状态 (IDLE/ASSIGNED/BUSY/REFUELING/MAINTENANCE)

容量约束型车辆 (FUEL, BAG) 在资源耗尽时进入 REFUELING 状态，
区别于普通 BUSY，调度器需感知此差异。
"""
from models import db
from models.vehicle import Vehicle


class VehicleManager:
    """车辆状态管理与维保记录."""

    # 状态常量
    IDLE = "IDLE"
    ASSIGNED = "ASSIGNED"
    BUSY = "BUSY"
    REFUELING = "REFUELING"
    MAINTENANCE = "MAINTENANCE"

    @staticmethod
    def set_status(vehicle_id: int, status: str) -> bool:
        """更新车辆状态."""
        vehicle = db.session.get(Vehicle, vehicle_id)
        if not vehicle:
            return False
        vehicle.status = status
        db.session.commit()
        return True

    @staticmethod
    def get_available_vehicles(vehicle_type: str, variant: str = None,
                               region_id: int = None) -> list:
        """查询可用车辆，支持按车型、等级、区域过滤."""
        query = Vehicle.query.filter_by(type=vehicle_type, status="IDLE")
        if variant:
            query = query.filter_by(variant=variant)
        if region_id:
            query = query.filter_by(region_id=region_id)
        return query.all()

    @staticmethod
    def mark_refueling(vehicle_id: int, fuel_remaining_l: int = 0) -> bool:
        """加油车/行李车资源耗尽，标记为回补状态."""
        vehicle = db.session.get(Vehicle, vehicle_id)
        if not vehicle:
            return False
        vehicle.status = VehicleManager.REFUELING
        # 记录当前资源余量
        if vehicle.attributes is None:
            vehicle.attributes = {}
        vehicle.attributes["fuel_remaining_l"] = fuel_remaining_l
        db.session.commit()
        return True

    @staticmethod
    def complete_refueling(vehicle_id: int) -> bool:
        """回补完成，恢复 IDLE."""
        vehicle = db.session.get(Vehicle, vehicle_id)
        if not vehicle:
            return False
        vehicle.status = VehicleManager.IDLE
        # 恢复满容量（从 catalog 读取默认容量）
        vehicle.attributes = vehicle.attributes or {}
        vehicle.attributes["fuel_remaining_l"] = vehicle.attributes.get("capacity_l", 20000)
        db.session.commit()
        return True

    @staticmethod
    def relocate_vehicle(vehicle_id: int, target_region_id: int) -> bool:
        """将车辆调度到指定区域."""
        vehicle = db.session.get(Vehicle, vehicle_id)
        if not vehicle:
            return False
        vehicle.region_id = target_region_id
        db.session.commit()
        return True
