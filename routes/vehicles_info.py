"""车辆信息表路由."""
from flask import render_template
from models.vehicle import VehicleInfo, VehicleStatus
from models import db
from . import vehicles_bp


TYPE_NAMES = {
    "TOW": "牵引车",
    "GPU": "电源车",
    "STAIR": "客梯车",
    "BUS": "摆渡车",
    "FUEL": "加油车",
    "BAG": "行李车",
}

STATUS_NAMES = {
    "IDLE": "空闲",
    "ASSIGNED": "已分配",
    "BUSY": "工作中",
    "MAINTENANCE": "维修中",
}


@vehicles_bp.route("/vehicles/table")
def vehicles_table():
    rows = db.session.query(VehicleInfo, VehicleStatus).join(
        VehicleStatus, VehicleInfo.plate_number == VehicleStatus.plate_number
    ).order_by(VehicleInfo.vehicle_type, VehicleInfo.plate_number).all()

    return render_template("vehicles_table.html", rows=rows,
                           TYPE_NAMES=TYPE_NAMES, STATUS_NAMES=STATUS_NAMES)
