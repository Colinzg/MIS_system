"""调度看板路由 — 对应进度监控子系统的可视化入口."""
from flask import render_template
from models.flight import Flight
from models.task import Task
from models.vehicle import Vehicle
from . import dashboard_bp


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
def dashboard():
    """调度员任务看板：显示所有航班及其任务状态."""
    flights = Flight.query.order_by(Flight.scheduled_at).all()
    tasks = Task.query.order_by(Task.created_at.desc()).limit(50).all()
    vehicles = Vehicle.query.order_by(Vehicle.type, Vehicle.plate).all()
    return render_template("dashboard.html", flights=flights, tasks=tasks, vehicles=vehicles)
