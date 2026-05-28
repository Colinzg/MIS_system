"""路径计算子系统 — 基于路网和车辆位置计算行驶路径与预估时间.

职责 (对应 UC 矩阵):
  - 读取: 机场路网数据、车辆基础信息、地面服务任务
  - 创建: 行驶路径（含路径点序列、预估时间）

数据流向: 路径计算 → 调度规划 (派单时参考) + 司机终端 (导航)

待实现: Dijkstra / A* 最短路径，届时需导入 models.road_network。
"""


class PathCalculator:
    """基于路网拓扑的最短路径计算."""

    @staticmethod
    def shortest_path(from_node_id: int, to_node_id: int) -> dict:
        """计算两点间最短路径（Dijkstra）.

        Args:
            from_node_id: 起点节点 ID
            to_node_id: 终点节点 ID

        Returns:
            {"path": [node_id, ...], "total_distance_m": float, "total_duration_min": float}
            若不可达则 path 为空列表
        """
        # 暂存: 待实现 Dijkstra / A*
        return {"path": [], "total_distance_m": 0, "total_duration_min": 0}

    @staticmethod
    def estimate_duration(vehicle_id: int, task_region_id: int) -> float:
        """预估车辆从当前位置到任务区域的通行时间（分钟）."""
        return 0.0
