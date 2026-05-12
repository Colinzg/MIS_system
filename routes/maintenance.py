"""基础数据维护路由 — 对应基础数据维护子系统的配置界面."""
from flask import render_template
from . import maintenance_bp


@maintenance_bp.route("/maintenance")
def maintenance_index():
    """基础数据维护首页."""
    return render_template("maintenance.html")
