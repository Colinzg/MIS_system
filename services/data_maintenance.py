"""基础数据维护子系统 — 维护航班、机位、路网、车辆等数据.

职责 (对应 UC 矩阵):
  - 创建: 航班信息、停机位、机场路网数据、车辆信息
"""
from models import db
from models.flight import Flight
from models.gate import Gate
from models.road_network import RoadNode, RoadEdge
from models.vehicle import VehicleInfo, VehicleStatus


class DataMaintenance:
    """基础数据 CRUD 维护."""

    # ── 航班 ────────────────────────────────────────────

    @staticmethod
    def create_flight(flight_no: str, airline: str, aircraft_type: str,
                      scheduled_at, gate_id: int = None, region_id: int = None,
                      needs_fuel: bool = False) -> Flight:
        flight = Flight(
            flight_no=flight_no, airline=airline, aircraft_type=aircraft_type,
            scheduled_at=scheduled_at, gate_id=gate_id, region_id=region_id,
            needs_fuel=needs_fuel,
        )
        db.session.add(flight)
        db.session.commit()
        return flight

    # ── 停机位 ──────────────────────────────────────────

    @staticmethod
    def create_gate(code: str, region_id: int, has_jet_bridge: bool = True) -> Gate:
        gate = Gate(code=code, region_id=region_id, has_jet_bridge=has_jet_bridge)
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
    def create_vehicle(plate_number: str, vehicle_type: str, brand_model: str,
                       region: str = None) -> VehicleInfo:
        vinfo = VehicleInfo(
            plate_number=plate_number, vehicle_type=vehicle_type,
            brand_model=brand_model, region=region,
        )
        db.session.add(vinfo)
        vstat = VehicleStatus(plate_number=plate_number, current_status="IDLE")
        db.session.add(vstat)
        db.session.commit()
        return vinfo
