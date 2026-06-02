"""Gate — 停机位.

每个停机位属于一个区域，has_jet_bridge 决定是否需要客梯车和摆渡车。
"""
from models import db


class Gate(db.Model):
    __tablename__ = "gates"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(8), unique=True, nullable=False, comment="机位代码，如 A01")
    region_id = db.Column(
        db.Integer,
        db.ForeignKey("regions.id"),
        nullable=False,
        comment="所属区域",
    )
    has_jet_bridge = db.Column(
        db.Boolean, default=True, comment="是否有廊桥；无廊桥需客梯车+摆渡车"
    )
    # relationships
    region = db.relationship("Region", backref="gates")
    flights = db.relationship("Flight", back_populates="gate")

    def __repr__(self):
        return f"<Gate {self.code} jet_bridge={self.has_jet_bridge}>"
