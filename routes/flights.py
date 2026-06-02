"""航班信息表路由."""
from datetime import datetime, timedelta
from flask import render_template
from models.flight import Flight
from models.task import Task
from . import flights_bp


STATUS_NAMES = {
    "SCHEDULED": "已排班",
    "ARRIVED": "已入位",
    "DEPARTED": "已离场",
    "CANCELLED": "已取消",
}


@flights_bp.route("/flights")
def flights():
    now = datetime.utcnow() + timedelta(hours=8)
    flights = Flight.query.order_by(Flight.scheduled_at).all()

    rows = []
    for f in flights:
        total = Task.query.filter_by(flight_id=f.id).count()
        done = Task.query.filter_by(flight_id=f.id).filter(
            Task.status.in_(["COMPLETED"])
        ).count()
        pending = Task.query.filter_by(flight_id=f.id, status="PENDING").count()
        rows.append({
            "flight": f,
            "total": total,
            "done": done,
            "pending": pending,
        })

    return render_template("flights.html", rows=rows, now=now, STATUS_NAMES=STATUS_NAMES)
