"""Flight — 航班信息.

每个航班关联一个停机位 (gate_id)，停机位属性决定保障任务类型。
"""
from datetime import datetime
from models import db


class Flight(db.Model):
    __tablename__ = "flights"

    id = db.Column(db.Integer, primary_key=True)
    flight_no = db.Column(db.String(16), unique=True, nullable=False, comment="航班号")
    airline = db.Column(db.String(32), nullable=False, comment="航空公司")
    aircraft_type = db.Column(
        db.String(10), nullable=True, comment="机型，如 A320 / B777，用于匹配 AircraftType 规则"
    )
    scheduled_at = db.Column(db.DateTime, nullable=False, comment="计划起飞时间")
    arrival_at = db.Column(
        db.DateTime, nullable=True, comment="预计到达机位时间，早于 scheduled_at"
    )
    gate_id = db.Column(
        db.Integer,
        db.ForeignKey("gates.id"),
        nullable=True,
        comment="停机位",
    )
    region_id = db.Column(
        db.Integer,
        db.ForeignKey("regions.id"),
        nullable=True,
        comment="所在区域（冗余，可通过 gate 推导）",
    )
    needs_fuel = db.Column(
        db.Boolean, default=False, comment="是否需要加油；非刚性需求，由航司决定"
    )
    status = db.Column(
        db.String(16),
        default="SCHEDULED",
        comment="状态: SCHEDULED / ARRIVED / DEPARTED / CANCELLED",
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    region = db.relationship("Region", back_populates="flights")
    gate = db.relationship("Gate", back_populates="flights")
    tasks = db.relationship("Task", back_populates="flight", lazy="dynamic")

    def __repr__(self):
        return f"<Flight {self.flight_no}>"
