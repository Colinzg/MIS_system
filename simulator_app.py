"""车载终端模拟器 — 独立应用，运行在另一端口，与调度中心通过 API 通讯.

启动方式:
    python simulator_app.py                            # 演示模式，可切换车辆
    python simulator_app.py -v 民航-B2001              # 固定车辆
    python simulator_app.py -v 民航-B2001 --port 5002  # 固定车辆 + 指定端口
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template
from models import db
from models.vehicle import VehicleInfo, VehicleStatus
from models.task import Task


def create_simulator_app(plate_number=None):
    """创建车载终端 app。plate_number=None 时为演示模式（可切换车辆）。"""
    app = Flask(__name__)
    app.config.from_object("config.Config")
    db.init_app(app)

    @app.route("/")
    @app.route("/<pn>")
    def terminal(pn=None):
        from datetime import datetime, timedelta

        now = datetime.utcnow() + timedelta(hours=8)
        vehicles = db.session.query(VehicleInfo, VehicleStatus).join(
            VehicleStatus, VehicleInfo.plate_number == VehicleStatus.plate_number
        ).order_by(VehicleInfo.vehicle_type, VehicleInfo.plate_number).all()

        # 确定当前选中的车辆
        target = pn if pn else (plate_number if plate_number else None)
        selected_info = None
        selected_status = None
        if target:
            selected_info = db.session.get(VehicleInfo, target)
            selected_status = db.session.query(VehicleStatus).filter_by(plate_number=target).first()
        if not selected_info and vehicles:
            selected_info, selected_status = vehicles[0]

        active_task = None
        if selected_info:
            active_task = Task.query.filter(
                Task.plate_number == selected_info.plate_number,
                Task.status.in_(["ASSIGNED", "CONFIRMED", "IN_PROGRESS"]),
            ).order_by(Task.scheduled_start.desc()).first()

        return render_template(
            "simulator_page.html",
            vehicles=vehicles,
            selected_info=selected_info,
            selected_status=selected_status,
            active_task=active_task,
            now=now,
        )

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="车载终端模拟器")
    parser.add_argument("-v", "--vehicle", type=str, default=None, help="车牌号（默认演示模式）")
    parser.add_argument("--port", type=int, default=5001, help="端口号")
    args = parser.parse_args()

    app = create_simulator_app(plate_number=args.vehicle)
    app.run(debug=True, port=args.port, use_reloader=False)
