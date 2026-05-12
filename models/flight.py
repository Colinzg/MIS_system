"""Flight — 航班信息.

包含航班号、航空公司、计划时间、所在区域等基本字段。
每个航班可以关联多个保障任务（Task）。
"""
from datetime import datetime
from models import db


class Flight(db.Model):
    __tablename__ = "flights"

    id = db.Column(db.Integer, primary_key=True)
    flight_no = db.Column(db.String(16), unique=True, nullable=False, comment="航班号")
    airline = db.Column(db.String(32), nullable=False, comment="航空公司")
    aircraft_type = db.Column(
        db.String(10), nullable=True, comment="机型，如 A320 / B777，用于匹配 AircraftResource 规则"
    )
    scheduled_at = db.Column(db.DateTime, nullable=False, comment="计划时间")
    gate = db.Column(db.String(8), nullable=True, comment="登机口")
    region_id = db.Column(
        db.Integer,
        db.ForeignKey("regions.id"),
        nullable=True,
        comment="所在区域",
    )
    status = db.Column(
        db.String(16),
        default="SCHEDULED",
        comment="状态: SCHEDULED / ARRIVED / DEPARTED / CANCELLED",
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    region = db.relationship("Region", back_populates="flights")
    tasks = db.relationship("Task", back_populates="flight", lazy="dynamic")

    def __repr__(self):
        return f"<Flight {self.flight_no}>"
