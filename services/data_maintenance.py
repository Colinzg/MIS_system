"""基础数据维护子系统 — 维护航班、机位、路网、车辆等数据.

职责 (对应 UC 矩阵):
  - 创建: 航班信息、停机位、机场路网数据、车辆基础信息

作为所有其他子系统的静态数据源，提供 CRUD 操作接口。
注意: 保障规则不再由数据表维护，而是由 AircraftType Python 类承载。
"""
from models import db
from models.flight import Flight
from models.gate import Gate
from models.road_network import RoadNode, RoadEdge
from models.vehicle import Vehicle


class DataMaintenance:
    """基础数据 CRUD 维护."""

    # ── 航班 ────────────────────────────────────────────

    @staticmethod
    def create_flight(flight_no: str, airline: str, aircraft_type: str,
                      scheduled_at, gate_id: int = None, region_id: int = None) -> Flight:
        flight = Flight(
            flight_no=flight_no, airline=airline, aircraft_type=aircraft_type,
            scheduled_at=scheduled_at, gate_id=gate_id, region_id=region_id,
        )
        db.session.add(flight)
        db.session.commit()
        return flight

    # ── 停机位 ──────────────────────────────────────────

    @staticmethod
    def create_gate(code: str, region_id: int, has_jet_bridge: bool = True,
                    x: float = None, y: float = None) -> Gate:
        gate = Gate(code=code, region_id=region_id, has_jet_bridge=has_jet_bridge,
                    x=x, y=y)
        db.session.add(gate)
        db.session.commit()
        return gate

    # ── 路网 ────────────────────────────────────────────

    @staticmethod
    def create_road_node(code: str, node_type: str, name: str = None,
                         region_id: int = None) -> RoadNode:
        node = RoadNode(code=code, node_type=node_type, name=name,
                        region_id=region_id)
        db.session.add(node)
        db.session.commit()
        return node

    @staticmethod
    def create_road_edge(from_node_id: int, to_node_id: int,
                         distance_m: float, duration_min: float,
                         is_two_way: bool = True) -> RoadEdge:
        edge = RoadEdge(from_node_id=from_node_id, to_node_id=to_node_id,
                        distance_m=distance_m, duration_min=duration_min,
                        is_two_way=is_two_way)
        db.session.add(edge)
        db.session.commit()
        return edge

    # ── 车辆 ────────────────────────────────────────────

    @staticmethod
    def create_vehicle(plate: str, vehicle_type: str, variant: str = None,
                       region_id: int = None, attributes: dict = None) -> Vehicle:
        vehicle = Vehicle(plate=plate, type=vehicle_type, variant=variant,
                          region_id=region_id, attributes=attributes)
        db.session.add(vehicle)
        db.session.commit()
        return vehicle
