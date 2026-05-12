"""进度监控子系统 — 跟踪任务执行情况，识别异常并生成提醒.

职责 (对应 UC 矩阵):
  - 读取: 地面服务任务、调度分配结果、车辆状态
  - 创建: 异常提醒 (超时未到位、超时未完成)

数据流向: 进度监控 → 可视化模块 (调度员看板)
"""
from datetime import datetime, timedelta
from models import db
from models.task import Task


class Monitor:
    """任务执行监控与异常检测."""

    @staticmethod
    def check_overdue_tasks() -> list:
        """检查所有超时未完成的任务.

        Returns:
            [{"task_id": int, "flight_id": int, "task_type": str, "overdue_minutes": float}, ...]
        """
        now = datetime.utcnow()
        overdue = []
        tasks = Task.query.filter(
            Task.status.in_(["PENDING", "IN_PROGRESS"]),
            Task.scheduled_end < now,
        ).all()

        for task in tasks:
            overdue.append({
                "task_id": task.id,
                "flight_id": task.flight_id,
                "task_type": task.task_type,
                "overdue_minutes": (now - task.scheduled_end).total_seconds() / 60,
            })
        return overdue

    @staticmethod
    def check_unassigned_tasks() -> list:
        """检查所有未分配车辆的 PENDING 任务.

        Returns:
            [{"task_id": int, "flight_id": int, "task_type": str}, ...]
        """
        tasks = Task.query.filter_by(status="PENDING", vehicle_id=None).all()
        return [
            {"task_id": t.id, "flight_id": t.flight_id, "task_type": t.task_type}
            for t in tasks
        ]

    @staticmethod
    def get_flight_progress(flight_id: int) -> dict:
        """获取指定航班的全部任务执行进度."""
        tasks = Task.query.filter_by(flight_id=flight_id).all()
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == "COMPLETED")
        return {
            "flight_id": flight_id,
            "total": total,
            "completed": completed,
            "progress_pct": round(completed / total * 100, 1) if total else 0,
        }
