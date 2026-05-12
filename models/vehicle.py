"""Vehicle — 机场地面服务车辆.

支持四种车型，每种车型 2-3 辆，总数不超过 10 辆。

车型枚举:
  - FUEL  : 加油车
  - BAG   : 行李车
  - TOW   : 牵引车
  - STAIR : 客梯车

状态枚举: IDLE（空闲） / ASSIGNED（已分配） / CONFIRMED（已确认） / BUSY（工作中） / MAINTENANCE（维修中）
"""
from models import db


class Vehicle(db.Model):
    __tablename__ = "vehicles"

    id = db.Column(db.Integer, primary_key=True)
    plate = db.Column(db.String(16), unique=True, nullable=False, comment="车牌号")
    type = db.Column(
        db.String(8),
        nullable=False,
        comment="车型: FUEL / BAG / TOW / STAIR",
    )
    status = db.Column(
        db.String(16),
        default="IDLE",
        comment="状态: IDLE / ASSIGNED / CONFIRMED / BUSY / MAINTENANCE",
    )
    region_id = db.Column(
        db.Integer,
        db.ForeignKey("regions.id"),
        nullable=True,
        comment="当前所在区域ID",
    )
    attributes = db.Column(
        db.JSON,
        nullable=True,
        comment="差异化属性字典: service_mode, compatible_aircraft, base_duration_min, capacity 等",
    )

    # relationships
    region = db.relationship("Region", back_populates="vehicles")
    tasks = db.relationship("Task", back_populates="vehicle", lazy="dynamic")
    comm_logs = db.relationship("CommunicationLog", back_populates="vehicle", lazy="dynamic")

    def __repr__(self):
        return f"<Vehicle {self.plate} ({self.type})>"
