"""Aircraft_Resource — 飞机资源需求规则.

记录每种机型保障所需的车辆类型及数量，
是连接"航班"和"任务生成"的核心业务规则表。
"""
from models import db


class AircraftResource(db.Model):
    __tablename__ = "aircraft_resources"

    id = db.Column(db.Integer, primary_key=True)
    aircraft_type = db.Column(
        db.String(10), nullable=False, comment="机型，如 A320 / B777"
    )
    required_vehicle_type = db.Column(
        db.String(8), nullable=False, comment="所需车辆类型，如 FUEL / BAG / TOW"
    )
    quantity = db.Column(
        db.Integer, nullable=False, default=1, comment="所需数量"
    )

    def __repr__(self):
        return f"<AircraftResource {self.aircraft_type} - {self.required_vehicle_type} x{self.quantity}>"
