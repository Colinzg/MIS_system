"""车辆管理路由 — 对应车辆管理子系统的可视化入口."""
from flask import render_template
from models.vehicle import Vehicle
from . import vehicles_bp


@vehicles_bp.route("/vehicles")
def vehicle_list():
    """车辆状态页：显示所有车辆的实时位置与状态."""
    vehicles = Vehicle.query.order_by(Vehicle.type, Vehicle.plate).all()
    return render_template("vehicles.html", vehicles=vehicles)
