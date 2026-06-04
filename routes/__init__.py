"""路由蓝图注册入口.

按业务领域拆分路由，每个蓝图对应一个或一组子系统。
"""
from flask import Blueprint

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../templates")
schedule_bp = Blueprint("schedule", __name__)
vehicles_bp = Blueprint("vehicles", __name__, template_folder="../templates")
maintenance_bp = Blueprint("maintenance", __name__, template_folder="../templates")
manual_bp = Blueprint("manual", __name__, template_folder="../templates")
flights_bp = Blueprint("flights", __name__, template_folder="../templates")
logs_bp = Blueprint("logs", __name__, template_folder="../templates")
api_bp = Blueprint("api", __name__)

from . import dashboard  # noqa: E402, F401
from . import schedule  # noqa: E402, F401
from . import vehicles  # noqa: E402, F401
from . import vehicles_info  # noqa: E402, F401
from . import maintenance  # noqa: E402, F401
from . import manual  # noqa: E402, F401
from . import flights  # noqa: E402, F401
from . import logs  # noqa: E402, F401
from . import api  # noqa: E402, F401
