"""车辆管理子系统 — 维护车辆基础信息与实时状态.

职责 (对应 UC 矩阵):
  - 读取: 车辆基础信息、地面服务任务
  - 创建: 车辆状态 (空闲/作业中/故障/维修)

数据流向:
  - 车辆状态 → 调度规划 (选车依据)
  - 车辆状态 → 进度监控 (异常检测)
"""
from models import db
from models.vehicle import Vehicle


class VehicleManager:
    """车辆状态管理与维保记录."""

    @staticmethod
    def set_status(vehicle_id: int, status: str) -> bool:
        """更新车辆状态.

        Status 枚举: IDLE / BUSY / MAINTENANCE
        """
        vehicle = db.session.get(Vehicle, vehicle_id)
        if not vehicle:
            return False
        vehicle.status = status
        db.session.commit()
        return True

    @staticmethod
    def get_available_vehicles(vehicle_type: str, region_id: int = None):
        """查询可用车辆，支持按区域过滤."""
        query = Vehicle.query.filter_by(type=vehicle_type, status="IDLE")
        if region_id:
            query = query.filter_by(region_id=region_id)
        return query.all()

    @staticmethod
    def relocate_vehicle(vehicle_id: int, target_region_id: int) -> bool:
        """将车辆调度到指定区域（更新 region_id）."""
        vehicle = db.session.get(Vehicle, vehicle_id)
        if not vehicle:
            return False
        vehicle.region_id = target_region_id
        db.session.commit()
        return True
