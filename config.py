import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """应用全局配置."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    # MySQL 连接（请先手动创建数据库）
    # 格式: mysql+pymysql://用户名:密码@主机:端口/库名?charset=utf8mb4
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://root:274156@localhost:3306/airport_scheduling?charset=utf8mb4",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
