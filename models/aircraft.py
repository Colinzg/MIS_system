"""AircraftType — 机型领域知识（非数据库模型）.

从 aircraft_catalog.json 加载技术参数，封装保障规则推导逻辑。
规则由物理参数推导而来，不是可自由配置的——因此用 Python 类方法而非数据库表。
"""
import json
import os
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


class AircraftType:
    """单个机型的领域知识：技术参数 + 保障规则推导."""

    def __init__(self, entry: dict):
        self.type = entry["type"]
        self.name = entry["name"]
        self.category = entry["category"]
        self.door_height_m = entry["dimensions"]["door_height_m"]
        self.max_takeoff_t = entry["weight"]["max_takeoff_t"]
        self.typical_passengers = entry["capacity"]["typical_passengers"]
        self.fuel_capacity_l = entry["capacity"]["fuel_capacity_l"]
        self.cabin_doors = entry["technical"]["cabin_doors"]

    # ── 规则推导 ────────────────────────────────────────────

    def required_tow_class(self) -> str:
        """根据最大起飞重量推导所需牵引车等级."""
        if self.max_takeoff_t <= 100:
            return "标准型"
        elif self.max_takeoff_t <= 400:
            return "重型"
        else:
            return "超重型"

    def required_stair_class(self) -> str:
        """根据舱门高度推导所需客梯车等级."""
        if self.door_height_m <= 4.0:
            return "标准型"
        elif self.door_height_m <= 5.5:
            return "高管型"
        else:
            return "超高管型"

    def required_fuel_class(self) -> str:
        """根据油箱容量推导所需加油车等级."""
        if self.fuel_capacity_l <= 30000:
            return "标准型"
        else:
            return "大容量型"

    def bus_class(self) -> str:
        """根据旅客数推导所需摆渡车等级."""
        return "大型" if self.typical_passengers > 200 else "小型"

    def baggage_vehicle_count(self) -> int:
        """根据旅客行李量推导所需行李车数量（每 100 人约需 1 辆车）."""
        return max(1, self.typical_passengers // 100 + 1)

    def bus_count(self) -> int:
        """根据旅客数推导所需摆渡车数量（每辆大型车 120 人，至少 1 辆）."""
        if self.bus_class() == "大型":
            return max(1, self.typical_passengers // 120 + 1)
        return max(1, self.typical_passengers // 50 + 1)

    def stair_count(self) -> int:
        """根据舱门数推导所需客梯车数量（通常每 2-4 个使用中的舱门配一辆）."""
        return max(1, self.cabin_doors // 4)

    # ── 任务生成 ────────────────────────────────────────────

    def generate_tasks(self, gate_has_jet_bridge: bool) -> list:
        """生成该机型在一次过站保障中的全部任务清单.

        Args:
            gate_has_jet_bridge: 停机位是否有廊桥

        Returns:
            [{"type": str, "quantity": int, "variant": str|None, "depends_on_type": str|None}, ...]
            depends_on_type 用于设置任务依赖链。
        """
        tasks = []

        # GPU — 全程连接，最先上
        tasks.append({"type": "GPU", "quantity": 1, "variant": "通用型", "depends_on_type": None})

        # STAIR + BUS — 仅无廊桥机位需要
        if not gate_has_jet_bridge:
            tasks.append({
                "type": "STAIR", "quantity": self.stair_count(),
                "variant": self.required_stair_class(), "depends_on_type": None,
            })
            tasks.append({
                "type": "BUS", "quantity": self.bus_count(),
                "variant": self.bus_class(), "depends_on_type": "STAIR",
            })

        # BAG — 依赖 STAIR（旅客下机后才能卸行李，无廊桥时）；有廊桥时无前置
        tasks.append({
            "type": "BAG", "quantity": self.baggage_vehicle_count(),
            "variant": "通用型",
            "depends_on_type": "STAIR" if not gate_has_jet_bridge else None,
        })

        # CLEAN — 过站清洁，在行李卸货后
        tasks.append({
            "type": "CLEAN", "quantity": 1, "variant": "通用型",
            "depends_on_type": "BAG",
        })

        # FUEL — 可并行，无严格前置
        tasks.append({
            "type": "FUEL", "quantity": 1,
            "variant": self.required_fuel_class(), "depends_on_type": None,
        })

        # TOW — 最后一步，依赖 CLEAN（依赖链末端），调度器额外检查全部任务完成
        tasks.append({
            "type": "TOW", "quantity": 1,
            "variant": self.required_tow_class(), "depends_on_type": "CLEAN",
        })

        return tasks


class AircraftCatalog:
    """机型目录：从 aircraft_catalog.json 加载全部机型，提供查询接口."""

    _instance: Optional["AircraftCatalog"] = None
    _catalog: dict = {}

    def __init__(self):
        if AircraftCatalog._instance is not None:
            return
        self._load()
        AircraftCatalog._instance = self

    def _load(self):
        path = os.path.join(DATA_DIR, "aircraft_catalog.json")
        with open(path, "r", encoding="utf-8") as f:
            entries = json.load(f)
        self._catalog = {e["type"]: AircraftType(e) for e in entries}

    @classmethod
    def get(cls, aircraft_type: str) -> Optional[AircraftType]:
        """按机型代码获取 AircraftType."""
        if cls._instance is None:
            cls()
        return cls._instance._catalog.get(aircraft_type)

    @classmethod
    def all_types(cls) -> list:
        """返回所有机型代码."""
        if cls._instance is None:
            cls()
        return list(cls._instance._catalog.keys())
