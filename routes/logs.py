"""管理日志 — 今日已保障航班记录.

展示今日已离场 (DEPARTED) 航班的完整保障信息：
  - 航班基本信息（航班号、航司、机型、停机位）
  - 入位/离场时间
  - 保障任务清单（任务类型、车辆、计划用时）
  - 车辆相关信息
"""
from datetime import datetime, timedelta

from flask import Blueprint, render_template

from models import db
from models.flight import Flight
from models.task import Task
from models.vehicle import VehicleInfo
from routes import logs_bp

# 任务类型 → 图标 + 中文名
TASK_TYPE_META = {
    "TOW":   {"icon": "🚜", "name": "牵引车"},
    "GPU":   {"icon": "⚡", "name": "电源车"},
    "STAIR": {"icon": "🪜", "name": "客梯车"},
    "BUS":   {"icon": "🚌", "name": "摆渡车"},
    "FUEL":  {"icon": "⛽", "name": "加油车"},
    "BAG":   {"icon": "🧳", "name": "行李车"},
    "CLEAN": {"icon": "🧹", "name": "清洁车"},
}


@logs_bp.route("/logs")
def logs():
    """今日已保障航班日志."""
    now = datetime.utcnow() + timedelta(hours=8)  # 北京时间
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    # 查询今日已离场的航班
    departed_flights = (
        Flight.query
        .filter(
            Flight.status == "DEPARTED",
            Flight.scheduled_at >= today_start,
            Flight.scheduled_at < today_end,
        )
        .order_by(Flight.scheduled_at.desc())
        .all()
    )

    # 为每个航班组装保障日志
    flight_logs = []
    all_vehicles = set()
    total_tasks = 0

    for flight in departed_flights:
        # 获取该航班的所有任务（含未完成的也列出来，用于全面了解情况）
        tasks = (
            Task.query
            .filter_by(flight_id=flight.id)
            .order_by(Task.scheduled_start)
            .all()
        )

        task_list = []
        for t in tasks:
            meta = TASK_TYPE_META.get(t.task_type, {"icon": "📋", "name": t.task_type})
            vehicle_info = None
            if t.plate_number:
                vehicle_info = db.session.get(VehicleInfo, t.plate_number)
                if vehicle_info:
                    all_vehicles.add(t.plate_number)

            # 计算任务计划用时
            duration_min = None
            if t.scheduled_start and t.scheduled_end:
                duration_min = int(
                    (t.scheduled_end - t.scheduled_start).total_seconds() / 60
                )

            task_list.append({
                "id": t.id,
                "type": t.task_type,
                "icon": meta["icon"],
                "type_name": meta["name"],
                "status": t.status,
                "plate_number": t.plate_number,
                "brand_model": vehicle_info.brand_model if vehicle_info else None,
                "scheduled_start": t.scheduled_start,
                "scheduled_end": t.scheduled_end,
                "duration_min": duration_min,
            })

        # 计算过站时间（入位 → 计划离场）
        turnaround_min = None
        if flight.arrival_at and flight.scheduled_at:
            turnaround_min = int(
                (flight.scheduled_at - flight.arrival_at).total_seconds() / 60
            )

        completed_count = sum(1 for t in task_list if t["status"] == "COMPLETED")
        total_tasks += len(task_list)

        flight_logs.append({
            "id": flight.id,
            "flight_no": flight.flight_no,
            "airline": flight.airline,
            "aircraft_type": flight.aircraft_type or "—",
            "gate_code": flight.gate.code if flight.gate else "—",
            "arrival_at": flight.arrival_at,
            "scheduled_at": flight.scheduled_at,
            "turnaround_min": turnaround_min,
            "tasks": task_list,
            "task_done": completed_count,
            "task_total": len(task_list),
        })

    return render_template(
        "logs.html",
        flight_logs=flight_logs,
        total_flights=len(flight_logs),
        total_tasks=total_tasks,
        total_vehicles=len(all_vehicles),
        now=now,
    )
