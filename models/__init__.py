"""导出所有模型以便 db.create_all() 一次性注册."""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .region import Region  # noqa: E402, F401
from .vehicle import Vehicle  # noqa: E402, F401
from .flight import Flight  # noqa: E402, F401
from .task import Task  # noqa: E402, F401
