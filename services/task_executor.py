"""任务执行子系统 — 自动完成任务、释放车辆资源、推进航班状态.

职责:
  - 检查过期任务并自动标记为 COMPLETED
  - 释放完成任务的车辆回 IDLE 状态
  - 推进航班状态 (SCHEDULED → ARRIVED → DEPARTED)

由后台线程周期性调用（每 10 秒），也可通过 POST /api/tick 手动触发。
"""
from datetime import datetime, timedelta
from models import db
from models.task import Task
from models.flight import Flight
from models.vehicle import VehicleStatus


class TaskExecutor:
    """自动任务执行与资源回收."""

    @staticmethod
    def run_cycle() -> dict:
        """执行一个完整的检查周期，推进所有过期状态.

        由后台线程周期性调用，也可通过 POST /api/tick 手动触发。
        每个周期在独立的 DB session 中运行，结束时清理 session。
        """
        now = datetime.utcnow() + timedelta(hours=8)  # 北京时间
        result = {
            "flights_arrived": [],
            "tasks_completed": 0,
            "vehicles_released": [],
            "flights_departed": [],
        }
        committed = False

        try:
            # ── 1. 航班自动入位：arrival_at 已过的 SCHEDULED 航班 → ARRIVED ──
            arrived_flights = Flight.query.filter(
                Flight.status == "SCHEDULED",
                Flight.arrival_at.isnot(None),
                Flight.arrival_at <= now,
            ).all()
            for f in arrived_flights:
                f.status = "ARRIVED"
                result["flights_arrived"].append(f.flight_no)

            # ── 2. 过期任务自动完成 + 释放车辆 ──
            overdue_tasks = Task.query.filter(
                Task.status == "IN_PROGRESS",
                Task.scheduled_end.isnot(None),
                Task.scheduled_end <= now,
            ).all()
            for task in overdue_tasks:
                task.status = "COMPLETED"
                result["tasks_completed"] += 1
                if task.plate_number:
                    vstat = VehicleStatus.query.filter_by(
                        plate_number=task.plate_number
                    ).first()
                    if vstat and vstat.current_status in ("ASSIGNED", "BUSY"):
                        vstat.current_status = "IDLE"
                        vstat.current_task = None
                        vstat.assigned_aircraft = None
                        result["vehicles_released"].append(task.plate_number)

            # ── 3. 航班自动离场：所有任务已完成 且 scheduled_at 已过 → DEPARTED ──
            active_flights = Flight.query.filter(
                Flight.status.in_(["ARRIVED", "SCHEDULED"]),
                Flight.scheduled_at <= now,
            ).all()
            for flight in active_flights:
                all_tasks = Task.query.filter_by(flight_id=flight.id).all()
                if all_tasks and all(t.status == "COMPLETED" for t in all_tasks):
                    flight.status = "DEPARTED"
                    result["flights_departed"].append(flight.flight_no)

            # ── 4. 自动分配非阻塞的 PENDING 任务 ──
            # 当依赖任务完成后，之前被阻塞的任务可以分配了
            unassigned = (
                db.session.query(Task.flight_id)
                .filter(Task.status == "PENDING", Task.plate_number.is_(None))
                .distinct().all()
            )
            if unassigned:
                from services.scheduler import Scheduler
                scheduler = Scheduler()
                result["tasks_auto_assigned"] = 0
                for (flight_id,) in unassigned:
                    try:
                        r = scheduler.schedule_for_flight(flight_id)
                        result["tasks_auto_assigned"] += len(r["tasks"])
                    except Exception:
                        pass  # 单个航班失败不影响其他

            # ── 提交 ──
            if any(v for v in result.values() if v):
                db.session.commit()
                committed = True

        except Exception:
            db.session.rollback()
            raise
        finally:
            # 清理 session，确保下一个周期获得干净的连接
            db.session.remove()

        return result
