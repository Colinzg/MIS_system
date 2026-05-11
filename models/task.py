"""Task — 航班保障任务.

每个航班需要生成若干任务，每种任务类型对应一种车辆：
  - FUEL     → 加油车
  - BAG      → 行李车
  - TOW      → 牵引车
  - STAIR    → 客梯车

状态枚举: PENDING / IN_PROGRESS / COMPLETED / FAILED
"""
from datetime import datetime
from models import db


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    flight_id = db.Column(
        db.Integer, db.ForeignKey("flights.id"), nullable=False, comment="关联航班"
    )
    vehicle_id = db.Column(
        db.Integer,
        db.ForeignKey("vehicles.id"),
        nullable=True,
        comment="分配的车辆",
    )
    task_type = db.Column(
        db.String(8),
        nullable=False,
        comment="任务类型: FUEL / BAG / TOW / STAIR",
    )
    scheduled_start = db.Column(db.DateTime, nullable=True, comment="计划开始时间")
    scheduled_end = db.Column(db.DateTime, nullable=True, comment="计划结束时间")
    status = db.Column(
        db.String(16),
        default="PENDING",
        comment="状态: PENDING / IN_PROGRESS / COMPLETED / FAILED",
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    flight = db.relationship("Flight", back_populates="tasks")
    vehicle = db.relationship("Vehicle", back_populates="tasks")

    def __repr__(self):
        return f"<Task {self.task_type} for {self.flight_id}>"
