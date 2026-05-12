"""CommunicationLog — 调度中心与车载终端通讯记录.

记录双方的消息往来，包括调度指令、任务确认、状态报告、告警等。
"""
from datetime import datetime
from models import db


class CommunicationLog(db.Model):
    __tablename__ = "communication_logs"

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(
        db.Integer, db.ForeignKey("vehicles.id"), nullable=False, comment="车辆 ID"
    )
    sender = db.Column(
        db.String(16), nullable=False, comment="发送方: DISPATCH / VEHICLE"
    )
    content = db.Column(db.Text, nullable=False, comment="消息内容")
    msg_type = db.Column(
        db.String(16), default="TEXT",
        comment="消息类型: TEXT / ACK / STATUS / ALERT / SOS",
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False, comment="调度员是否已读")

    # relationships
    vehicle = db.relationship("Vehicle", back_populates="comm_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "vehicle_id": self.vehicle_id,
            "vehicle_plate": self.vehicle.plate if self.vehicle else None,
            "sender": self.sender,
            "content": self.content,
            "msg_type": self.msg_type,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "read": self.read,
        }
