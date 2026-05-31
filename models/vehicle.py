"""Vehicle — 机场地面服务车辆.

车型枚举 (7 种):
  TOW   — 牵引车（推出飞机）
  GPU   — 地面电源车（全程供电）
  STAIR — 客梯车（无廊桥机位旅客上下）
  BUS   — 摆渡车（无廊桥机位旅客运输）
  FUEL  — 加油车（燃油加注）
  BAG   — 行李车（行李运输）
  CLEAN — 清洁车（过站保障）

状态枚举:
  IDLE        — 空闲
  ASSIGNED    — 已分配待确认
  BUSY        — 工作中
  REFUELING   — 回补中（加油车回油库 / 行李车回分拣区卸空）
  MAINTENANCE — 维修中

variant 字段指向 vehicle_catalog.json 中该车型的具体等级（如 "重型" / "标准型"）。
attributes JSON 仅存实例级动态数据（如当前油量、当前装载量）。
"""
from models import db


class Vehicle(db.Model):
    __tablename__ = "vehicles"

    id = db.Column(db.Integer, primary_key=True)
    plate = db.Column(db.String(16), unique=True, nullable=False, comment="车牌号")
    type = db.Column(
        db.String(8),
        nullable=False,
        comment="车型: TOW / GPU / STAIR / BUS / FUEL / BAG / CLEAN",
    )
    variant = db.Column(
        db.String(16),
        nullable=True,
        comment="车型等级，指向 vehicle_catalog.json variants.class，如 重型 / 标准型",
    )
    status = db.Column(
        db.String(16),
        default="IDLE",
        comment="状态: IDLE / ASSIGNED / BUSY / REFUELING / MAINTENANCE",
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
        comment="实例级动态数据: fuel_remaining_l, baggage_load 等",
    )

    # relationships
    region = db.relationship("Region", back_populates="vehicles")
    tasks = db.relationship("Task", back_populates="vehicle", lazy="dynamic")
    comm_logs = db.relationship("CommunicationLog", back_populates="vehicle", lazy="dynamic")

    def __repr__(self):
        return f"<Vehicle {self.plate} ({self.type}/{self.variant})>"
