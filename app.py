"""Flask 应用工厂 — 只做组装，不写具体路由.

初始化顺序:
  1. 创建 Flask app
  2. 加载配置
  3. 初始化 db
  4. 注册所有蓝图
"""
from flask import Flask
from config import Config
from models import db


def create_app(config_class=Config):
    """应用工厂：只做组装，不修改数据库结构."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    # 注册路由蓝图
    from routes import dashboard_bp, schedule_bp, vehicles_bp, maintenance_bp, api_bp
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(vehicles_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(api_bp)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
