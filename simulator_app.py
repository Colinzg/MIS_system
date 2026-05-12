"""车载终端模拟器 — 独立应用，运行在另一端口，与调度中心通过 API 通讯.

演示模式（默认）：顶部可切换车辆，展示完整的任务派发→接收流程。
生产部署时用 -v 参数固定车辆。

启动方式:
    python simulator_app.py                   # 演示模式，可切换车辆
    python simulator_app.py -v 3              # 固定车辆 ID=3
    python simulator_app.py -v 3 --port 5002  # 固定车辆 + 指定端口
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template
from models import db
from models.vehicle import Vehicle
from models.task import Task


def create_simulator_app(vehicle_id=None):
    """创建车载终端 app。vehicle_id=None 时为演示模式（可切换车辆）。"""
    app = Flask(__name__)
    app.config.from_object("config.Config")
    db.init_app(app)

    @app.route("/")
    @app.route("/<int:vid>")
    def terminal(vid=None):
        from datetime import datetime, timedelta

        now = datetime.utcnow() + timedelta(hours=8)
        vehicles = Vehicle.query.order_by(Vehicle.type, Vehicle.plate).all()

        # 确定当前选中的车辆
        target = vid if vid else (vehicle_id if vehicle_id else None)
        selected = None
        if target:
            selected = db.session.get(Vehicle, target)
        if not selected and vehicles:
            selected = vehicles[0]

        active_task = None
        if selected:
            active_task = Task.query.filter_by(
                vehicle_id=selected.id, status="IN_PROGRESS"
            ).first()

        return render_template(
            "simulator_page.html",
            vehicles=vehicles,
            selected=selected,
            active_task=active_task,
            now=now,
        )

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="车载终端模拟器")
    parser.add_argument("-v", "--vehicle", type=int, default=None, help="车辆 ID（默认演示模式）")
    parser.add_argument("--port", type=int, default=5001, help="端口号")
    args = parser.parse_args()

    app = create_simulator_app(vehicle_id=args.vehicle)
    app.run(debug=True, port=args.port, use_reloader=False)
