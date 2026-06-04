"""Flask 应用工厂 — 只做组装，不写具体路由.

初始化顺序:
  1. 创建 Flask app
  2. 加载配置
  3. 初始化 db
  4. 注册所有蓝图

运行方式:
    python app.py

会自动同时启动:
  - 调度中心 http://localhost:5000
  - 车载终端模拟器 http://localhost:5001
"""

import os
import subprocess
import sys
import threading
import time
import traceback

from flask import Flask
from config import Config
from models import db


def create_app(config_class=Config):
    """应用工厂：只做组装，不修改数据库结构."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    # 跨域支持（车载终端 5001 → 调度中心 5000）
    @app.after_request
    def add_cors(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response

    # 注册路由蓝图
    from routes import dashboard_bp, schedule_bp, vehicles_bp, maintenance_bp, manual_bp, flights_bp, logs_bp, api_bp
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(vehicles_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(manual_bp)
    app.register_blueprint(flights_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(api_bp)

    return app


def _run_task_executor(app):
    """后台线程：周期性自动完成任务并推进航班状态."""
    time.sleep(3)  # 等 Flask 启动完毕
    cycle_count = 0
    while True:
        try:
            with app.app_context():
                from services.task_executor import TaskExecutor
                result = TaskExecutor.run_cycle()
                cycle_count += 1
                if any(v for v in result.values() if v):
                    print(f"[TaskExecutor #{cycle_count}] {result}")
                elif cycle_count % 6 == 0:  # 每 60 秒输出一次心跳
                    print(f"[TaskExecutor #{cycle_count}] 心跳正常，无过期任务")
        except Exception:
            print(f"[TaskExecutor #{cycle_count}] 异常:")
            traceback.print_exc()
        time.sleep(10)


if __name__ == "__main__":
    # 自动启动车载终端模拟器（绑定车辆 ID=1，独立进程，端口 5001）
    simulator_proc = subprocess.Popen(
        [sys.executable, os.path.join(os.path.dirname(__file__), "simulator_app.py"),
         "-v", "1"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )

    app = create_app()

    # 启动后台任务执行线程（自动完成任务 + 释放车辆 + 推进航班状态）
    executor_thread = threading.Thread(
        target=_run_task_executor, args=(app,), daemon=True, name="task-executor"
    )
    executor_thread.start()

    # Flask 启动后会在终端输出可点击的 URL（Ctrl+点击即可在默认浏览器打开）
    try:
        app.run(debug=True, use_reloader=False)
    finally:
        simulator_proc.terminate()
        simulator_proc.wait()