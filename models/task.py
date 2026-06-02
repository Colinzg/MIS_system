"""Task — 航班保障任务.

每个航班按 AircraftType.generate_tasks() 生成若干任务，涵盖 6 种车辆类型。
任务间通过 depends_on 形成依赖链，调度器按拓扑顺序分配。

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
    plate_number = db.Column(
        db.String(16),
        db.ForeignKey("vehicle_info.plate_number"),
        nullable=True,
        comment="分配的车牌号",
    )
    task_type = db.Column(
        db.String(8),
        nullable=False,
        comment="任务类型: TOW / GPU / STAIR / BUS / FUEL / BAG",
    )
    scheduled_start = db.Column(db.DateTime, nullable=True, comment="计划开始时间")
    scheduled_end = db.Column(db.DateTime, nullable=True, comment="计划结束时间")
    status = db.Column(
        db.String(16),
        default="PENDING",
        comment="状态: PENDING / IN_PROGRESS / COMPLETED / FAILED",
    )
    depends_on = db.Column(
        db.Integer,
        db.ForeignKey("tasks.id"),
        nullable=True,
        comment="前置任务 ID，用于表达任务依赖链",
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    flight = db.relationship("Flight", back_populates="tasks")
    vehicle = db.relationship("VehicleInfo", back_populates="tasks")

    def __repr__(self):
        return f"<Task {self.task_type} for flight#{self.flight_id}>"
