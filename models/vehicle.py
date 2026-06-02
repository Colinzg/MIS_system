"""VehicleModel / VehicleInfo / VehicleStatus — 机场地面服务车辆.

车辆数据分离为三张表：
  VehicleModel    — 车辆型号技术参数（来自 vehicle_models.json，以型号为对象）
  VehicleInfo     — 车辆静态信息（牌照、型号、购置日期），一次写入、极少变更
  VehicleStatus   — 实时状态（当前位置、任务、状态），随运行持续更新

车型枚举 (6 种):
  TOW   — 牵引车
  GPU   — 地面电源车
  STAIR — 客梯车
  BUS   — 摆渡车
  FUEL  — 加油车
  BAG   — 行李拖车

大小等级:
  小型 / 中型 / 大型     — 牵引车按牵引力等级
  小型 / 大型           — 电源车按输出功率
  标准 / 高升程         — 客梯车按最大工作高度
  标准 / 大型           — 摆渡车按载客量
  标准                  — 加油车、行李拖车通用

状态枚举:
  IDLE        — 空闲
  ASSIGNED    — 已分配待确认
  BUSY        — 工作中
  MAINTENANCE — 维修中
"""
from models import db


class VehicleModel(db.Model):
    """车辆型号技术参数 — 来自 vehicle_models.json，以型号为对象."""
    __tablename__ = "vehicle_models"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    vehicle_type = db.Column(
        db.String(8), nullable=False, index=True,
        comment="车型: TOW / GPU / STAIR / BUS / FUEL / BAG",
    )
    brand_model = db.Column(db.String(64), nullable=False, unique=True, comment="品牌型号")
    manufacturer = db.Column(db.String(64), nullable=True, comment="生产商")
    size_class = db.Column(db.String(8), nullable=True, comment="大小等级")
    specs = db.Column(db.JSON, nullable=True, comment="技术参数 JSON")
    compatible_aircraft = db.Column(db.JSON, nullable=True, comment="适用机型列表")
    base_duration_min = db.Column(db.Integer, nullable=True, comment="基准服务时长(分钟)")

    def __repr__(self):
        return f"<VehicleModel {self.brand_model} ({self.size_class}{self.vehicle_type})>"


class VehicleInfo(db.Model):
    __tablename__ = "vehicle_info"

    plate_number = db.Column(db.String(16), primary_key=True, comment="车牌号")
    vehicle_type = db.Column(
        db.String(8), nullable=False,
        comment="车型: TOW / GPU / STAIR / BUS / FUEL / BAG",
    )
    brand_model = db.Column(db.String(64), nullable=False, comment="品牌型号")
    size_class = db.Column(db.String(8), nullable=True, comment="大小等级（冗余，方便按等级查询）")
    region = db.Column(db.String(8), nullable=True, comment="所属区域 A / B")
    purchase_date = db.Column(db.Date, nullable=True, comment="购置日期")
    asset_tag = db.Column(db.String(32), nullable=True, comment="固定资产标签")
    remark = db.Column(db.String(128), nullable=True, comment="备注")

    # relationships
    status = db.relationship("VehicleStatus", back_populates="vehicle", uselist=False)
    tasks = db.relationship("Task", back_populates="vehicle", lazy="dynamic")
    comm_logs = db.relationship("CommunicationLog", back_populates="vehicle", lazy="dynamic")

    def __repr__(self):
        return f"<VehicleInfo {self.plate_number} ({self.vehicle_type}/{self.brand_model})>"


class VehicleStatus(db.Model):
    __tablename__ = "vehicle_status"

    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(
        db.String(16),
        db.ForeignKey("vehicle_info.plate_number"),
        nullable=False,
        unique=True,
        comment="车牌号",
    )
    current_status = db.Column(
        db.String(16), default="IDLE",
        comment="状态: IDLE / ASSIGNED / BUSY / MAINTENANCE",
    )
    current_location = db.Column(db.String(64), nullable=True, comment="当前位置")
    current_task = db.Column(db.String(64), nullable=True, comment="当前任务描述")
    assigned_aircraft = db.Column(db.String(16), nullable=True, comment="分配的航班号")

    # relationships
    vehicle = db.relationship("VehicleInfo", back_populates="status")

    def __repr__(self):
        return f"<VehicleStatus {self.plate_number} {self.current_status}>"
