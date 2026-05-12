"""基础数据维护子系统 — 维护航班、保障规则、路网、车辆等静态数据.

职责 (对应 UC 矩阵):
  - 创建: 航班信息、保障规则、机场路网数据、车辆基础信息

作为所有其他子系统的静态数据源，提供 CRUD 操作接口.
"""
from models import db
from models.flight import Flight
from models.aircraft_resource import AircraftResource
from models.road_network import RoadNode, RoadEdge
from models.vehicle import Vehicle


class DataMaintenance:
    """基础数据 CRUD 维护."""

    # ── 航班 ────────────────────────────────────────────

    @staticmethod
    def create_flight(flight_no: str, airline: str, aircraft_type: str,
                      scheduled_at, gate: str = None, region_id: int = None) -> Flight:
        flight = Flight(
            flight_no=flight_no, airline=airline, aircraft_type=aircraft_type,
            scheduled_at=scheduled_at, gate=gate, region_id=region_id,
        )
        db.session.add(flight)
        db.session.commit()
        return flight

    # ── 保障规则 ────────────────────────────────────────

    @staticmethod
    def upsert_resource_rule(aircraft_type: str, vehicle_type: str,
                             quantity: int) -> AircraftResource:
        rule = AircraftResource.query.filter_by(
            aircraft_type=aircraft_type, required_vehicle_type=vehicle_type
        ).first()
        if rule:
            rule.quantity = quantity
        else:
            rule = AircraftResource(
                aircraft_type=aircraft_type, required_vehicle_type=vehicle_type,
                quantity=quantity,
            )
            db.session.add(rule)
        db.session.commit()
        return rule

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
    def create_vehicle(plate: str, vehicle_type: str, region_id: int = None,
                       attributes: dict = None) -> Vehicle:
        vehicle = Vehicle(plate=plate, type=vehicle_type,
                          region_id=region_id, attributes=attributes)
        db.session.add(vehicle)
        db.session.commit()
        return vehicle
