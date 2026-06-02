"""车辆管理路由 — 对应车辆管理子系统的可视化入口."""
from flask import render_template
from models.vehicle import VehicleInfo, VehicleStatus
from models import db
from . import vehicles_bp


@vehicles_bp.route("/vehicles")
def vehicle_list():
    """车辆状态页：显示所有车辆的实时位置与状态."""
    vehicles = db.session.query(VehicleInfo, VehicleStatus).join(
        VehicleStatus, VehicleInfo.plate_number == VehicleStatus.plate_number
    ).order_by(VehicleInfo.vehicle_type, VehicleInfo.plate_number).all()
    return render_template("vehicles.html", vehicles=vehicles)
