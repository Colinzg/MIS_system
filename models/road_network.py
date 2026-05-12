"""RoadNetwork — 机场路网数据.

存储机场内部道路的节点和边，用于路径计算模块。
节点表示路口、机位、服务站等位置点，边表示路段（含距离与通行时间）。
"""
from models import db


class RoadNode(db.Model):
    __tablename__ = "road_nodes"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(
        db.String(16), unique=True, nullable=False, comment="节点代码，如 N01 / GATE-A12"
    )
    name = db.Column(db.String(64), nullable=True, comment="节点名称")
    node_type = db.Column(
        db.String(16),
        nullable=False,
        comment="节点类型: INTERSECTION / GATE / SERVICE_STATION",
    )
    region_id = db.Column(
        db.Integer, db.ForeignKey("regions.id"), nullable=True, comment="所属区域"
    )
    latitude = db.Column(db.Float, nullable=True, comment="纬度")
    longitude = db.Column(db.Float, nullable=True, comment="经度")

    def __repr__(self):
        return f"<RoadNode {self.code} ({self.node_type})>"


class RoadEdge(db.Model):
    __tablename__ = "road_edges"

    id = db.Column(db.Integer, primary_key=True)
    from_node_id = db.Column(
        db.Integer, db.ForeignKey("road_nodes.id"), nullable=False, comment="起点节点"
    )
    to_node_id = db.Column(
        db.Integer, db.ForeignKey("road_nodes.id"), nullable=False, comment="终点节点"
    )
    distance_m = db.Column(db.Float, nullable=False, comment="路段长度（米）")
    duration_min = db.Column(db.Float, nullable=False, comment="预计通行时间（分钟）")
    is_two_way = db.Column(db.Boolean, default=True, comment="是否双向通行")

    # relationships
    from_node = db.relationship(
        "RoadNode", foreign_keys=[from_node_id], backref="outgoing_edges"
    )
    to_node = db.relationship(
        "RoadNode", foreign_keys=[to_node_id], backref="incoming_edges"
    )

    def __repr__(self):
        return f"<RoadEdge {self.from_node_id} → {self.to_node_id} ({self.distance_m}m)>"
