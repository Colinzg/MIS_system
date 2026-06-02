"""车辆管理子系统 — 维护车辆实时状态.

职责 (对应 UC 矩阵):
  - 读取: vehicle_status 表、地面服务任务
  - 更新: 车辆状态 (IDLE/ASSIGNED/BUSY/MAINTENANCE)
"""
from models import db
from models.vehicle import VehicleInfo, VehicleStatus


class VehicleManager:
    """车辆状态管理."""

    IDLE = "IDLE"
    ASSIGNED = "ASSIGNED"
    BUSY = "BUSY"
    MAINTENANCE = "MAINTENANCE"

    @staticmethod
    def set_status(plate_number: str, status: str) -> bool:
        """更新车辆状态."""
        vstat = db.session.query(VehicleStatus).filter_by(plate_number=plate_number).first()
        if not vstat:
            return False
        vstat.current_status = status
        db.session.commit()
        return True

    @staticmethod
    def get_available_vehicles(vehicle_type: str, region: str = None) -> list:
        """查询可用车辆，支持按车型、区域过滤."""
        query = db.session.query(VehicleInfo, VehicleStatus).join(
            VehicleStatus, VehicleInfo.plate_number == VehicleStatus.plate_number
        ).filter(
            VehicleInfo.vehicle_type == vehicle_type,
            VehicleStatus.current_status == "IDLE",
        )
        if region:
            query = query.filter(VehicleInfo.region == region)
        return query.all()

    @staticmethod
    def relocate_vehicle(plate_number: str, target_region: str) -> bool:
        """将车辆调度到指定区域."""
        vinfo = db.session.get(VehicleInfo, plate_number)
        if not vinfo:
            return False
        vinfo.region = target_region
        db.session.commit()
        return True
