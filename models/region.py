"""Region — 机场区域.

存储机场的物理分区（如 A01 / B02 / C03），
车辆和航班通过 region_id 关联到所在区域。
"""
from models import db


class Region(db.Model):
    __tablename__ = "regions"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(8), unique=True, nullable=False, comment="区域代码，如 A01")
    name = db.Column(db.String(64), nullable=False, comment="区域名称，如 1号航站楼东侧")

    # relationships
    vehicles = db.relationship("Vehicle", back_populates="region", lazy="dynamic")
    flights = db.relationship("Flight", back_populates="region", lazy="dynamic")

    def __repr__(self):
        return f"<Region {self.code}>"
