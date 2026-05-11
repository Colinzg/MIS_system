"""Flask 应用入口 — 创建 app 并注册路由."""
from flask import Flask, flash, redirect, render_template, url_for
from config import Config
from models import db
from models.vehicle import Vehicle
from models.task import Task
from models.flight import Flight

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    with app.app_context():
        from models import (  # noqa: F401 — 触发注册以便 db.create_all
            Region,
            Vehicle,
            Flight,
            Task,
        )
        db.create_all()

    # ── 路由 ──────────────────────────────────────────────

    @app.route("/")
    @app.route("/dashboard")
    def dashboard():
        """调度员任务看板：显示所有航班及其任务状态."""
        flights = Flight.query.order_by(Flight.scheduled_at).all()
        tasks = Task.query.order_by(Task.created_at.desc()).limit(50).all()
        return render_template("dashboard.html", flights=flights, tasks=tasks)

    @app.route("/vehicles")
    def vehicles():
        """车辆状态页：显示所有车辆的实时位置与状态."""
        vehicles = Vehicle.query.order_by(Vehicle.type, Vehicle.plate).all()
        return render_template("vehicles.html", vehicles=vehicles)

    @app.route("/schedule/<int:flight_id>")
    def schedule_flight(flight_id):
        """为指定航班触发调度."""
        from services.scheduler import Scheduler

        result = Scheduler().schedule_for_flight(flight_id)
        assigned = len(result["tasks"])
        errors = result["errors"]
        if assigned:
            flash(f"成功调度 {assigned} 个任务", "success")
        if errors:
            for err in errors:
                flash(f"调度失败: {err}", "error")
        return redirect(url_for("dashboard"))

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
