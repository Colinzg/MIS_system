"""调度触发路由 — 对应调度规划子系统的接口."""
from flask import flash, redirect, url_for
from . import schedule_bp
from services.scheduler import Scheduler


@schedule_bp.route("/schedule/<int:flight_id>")
def schedule_flight(flight_id):
    """为指定航班触发调度."""
    result = Scheduler().schedule_for_flight(flight_id)
    assigned = len(result["tasks"])
    errors = result["errors"]
    if assigned:
        flash(f"成功调度 {assigned} 个任务", "success")
    if errors:
        for err in errors:
            flash(f"调度失败: {err}", "error")
    return redirect(url_for("dashboard.dashboard"))
