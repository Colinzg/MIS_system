"""数据模型注册入口.

使用延迟初始化模式：db = SQLAlchemy() 不绑定 app，
在 app.create_app() 中通过 db.init_app(app) 完成绑定。
所有模型在此导入以确保 db.create_all() 能发现全部表。
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .region import Region  # noqa: E402, F401
from .vehicle import Vehicle  # noqa: E402, F401
from .flight import Flight  # noqa: E402, F401
from .task import Task  # noqa: E402, F401
from .aircraft_resource import AircraftResource  # noqa: E402, F401
from .road_network import RoadNode, RoadEdge  # noqa: E402, F401
from .comm_log import CommunicationLog  # noqa: E402, F401
