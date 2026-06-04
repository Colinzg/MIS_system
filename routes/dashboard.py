"""调度看板路由 — 对应进度监控子系统的可视化入口."""
from datetime import datetime, timedelta
from flask import render_template
from models.flight import Flight
from models.task import Task
from models.vehicle import VehicleInfo, VehicleStatus
from models import db
from . import dashboard_bp


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
def dashboard():
    """调度员任务看板：显示所有航班及其任务状态."""
    now = datetime.utcnow() + timedelta(hours=8)  # 北京时间 (naive, 与 DB 一致)
    flights = Flight.query.filter(
        Flight.status.in_(["SCHEDULED", "ARRIVED"])
    ).order_by(Flight.scheduled_at).all()
    # 待分配任务按航班分组
    pending = Task.query.filter_by(status="PENDING").join(Task.flight).order_by(
        Flight.scheduled_at.asc(), Task.id
    ).all()
    # 进行中的任务（用于右侧追踪面板）
    active_tasks = Task.query.filter_by(status="IN_PROGRESS").join(Task.flight).order_by(
        Flight.scheduled_at.asc()
    ).all()
    vehicles = db.session.query(VehicleInfo, VehicleStatus).join(
        VehicleStatus, VehicleInfo.plate_number == VehicleStatus.plate_number
    ).order_by(VehicleInfo.vehicle_type, VehicleInfo.plate_number).all()

    # 构建 plate_number → VehicleStatus 映射，用于任务监控面板显示精确状态
    vstat_map = {vs.plate_number: vs for _, vs in vehicles}

    flight_groups = []
    for task in pending:
        if not flight_groups or flight_groups[-1]["flight"].id != task.flight_id:
            flight_groups.append({"flight": task.flight, "tasks": []})
        flight_groups[-1]["tasks"].append(task)

    return render_template("dashboard.html", flight_groups=flight_groups, flights=flights,
                           vehicles=vehicles, active_tasks=active_tasks, vstat_map=vstat_map, now=now)
