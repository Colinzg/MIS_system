"""工作手册 — Wiki 风格飞机/车辆技术参数查询."""
from flask import render_template
from models import db
from models.vehicle import Vehicle
from models.aircraft_resource import AircraftResource
from models.flight import Flight
from . import manual_bp


@manual_bp.route("/manual")
def manual():
    # ── 动态数据 ──────────────────────────────────
    vehicles = Vehicle.query.order_by(Vehicle.type, Vehicle.plate).all()
    rules = AircraftResource.query.order_by(
        AircraftResource.aircraft_type, AircraftResource.required_vehicle_type
    ).all()

    # 车型分组
    vtype_info = {}
    for v in vehicles:
        vtype_info.setdefault(v.type, {"vehicles": [], "total": 0})
        vtype_info[v.type]["vehicles"].append(v)
        vtype_info[v.type]["total"] += 1

    # 机型保障规则
    aircraft_rules = {}
    for r in rules:
        aircraft_rules.setdefault(r.aircraft_type, []).append(r)

    # 所有出现的机型
    db_types = (
        db.session.query(Flight.aircraft_type)
        .distinct().filter(Flight.aircraft_type.isnot(None)).all()
    )
    known_aircraft = sorted({at[0] for at in db_types} | set(aircraft_rules.keys()))

    # ── 静态参考数据 ──────────────────────────────

    # 飞机技术参数
    aircraft_specs = {
        "A320": {
            "name": "Airbus A320",
            "manufacturer": "空中客车 (Airbus)",
            "type": "单通道窄体客机",
            "length": "37.57 m",
            "wingspan": "35.80 m",
            "height": "11.76 m",
            "max_takeoff_weight": "78.0 t",
            "max_landing_weight": "66.0 t",
            "range": "6,100 km",
            "cruise_speed": "Mach 0.78",
            "seats": "150–180",
            "engine_options": "CFM56-5B / IAE V2500",
            "image_label": "A320",
            "description": (
                "Airbus A320 是空中客车公司研制的单通道双发窄体客机，"
                "是航空史上最畅销的机型之一。A320 系列包括 A318、A319、A320、A321 四个子型号，"
                "覆盖 100–240 座级。作为全球首款采用电传操纵（Fly-by-Wire）系统的量产客机，"
                "A320 在飞行安全性和操控性方面树立了新的标准。"
            ),
        },
        "B737": {
            "name": "Boeing 737",
            "manufacturer": "波音 (Boeing)",
            "type": "单通道窄体客机",
            "length": "39.50 m",
            "wingspan": "35.80 m",
            "height": "12.50 m",
            "max_takeoff_weight": "79.0 t",
            "max_landing_weight": "66.4 t",
            "range": "5,765 km",
            "cruise_speed": "Mach 0.79",
            "seats": "162–189",
            "engine_options": "CFM56-7B",
            "image_label": "B737-800",
            "description": (
                "Boeing 737 是波音公司生产的双发单通道窄体客机，"
                "是全球累计产量最高的喷气式客机系列。737 NG（Next Generation）系列包括 "
                "737-600/700/800/900 四个型号，其中 737-800 是最畅销的型号。"
                "该机型以可靠性和经济性著称，广泛用于中短程航线。"
            ),
        },
        "B777": {
            "name": "Boeing 777",
            "manufacturer": "波音 (Boeing)",
            "type": "双通道宽体客机",
            "length": "73.90 m",
            "wingspan": "64.80 m",
            "height": "18.50 m",
            "max_takeoff_weight": "351.0 t",
            "max_landing_weight": "251.0 t",
            "range": "13,650 km",
            "cruise_speed": "Mach 0.84",
            "seats": "301–368",
            "engine_options": "GE90-115B",
            "image_label": "B777-300ER",
            "description": (
                "Boeing 777 是波音公司生产的双发双通道宽体客机，"
                "是全球最大的双发客机。777-300ER 是 777 系列中最畅销的型号，"
                "搭载 GE90 系列发动机——全球推力最大的涡扇发动机。"
                "该机型以超长航程能力和燃油经济性著称，广泛用于跨洋航线。"
            ),
        },
        "A330": {
            "name": "Airbus A330",
            "manufacturer": "空中客车 (Airbus)",
            "type": "双通道宽体客机",
            "length": "63.69 m",
            "wingspan": "60.30 m",
            "height": "16.83 m",
            "max_takeoff_weight": "242.0 t",
            "max_landing_weight": "187.0 t",
            "range": "11,750 km",
            "cruise_speed": "Mach 0.82",
            "seats": "277–440",
            "engine_options": "Trent 700 / CF6-80E1",
            "image_label": "A330-300",
            "description": (
                "Airbus A330 是空中客车公司研制的双发双通道宽体客机，"
                "与四发的 A340 同时期开发。A330-300 是基础型号，"
                "具有优秀的燃油效率和舒适的客舱环境。"
                "A330neo 系列（-800/-900）配备了新一代发动机和鲨鳍小翼，"
                "进一步提升了经济性。"
            ),
        },
    }

    # 车辆技术参数
    vehicle_specs = {
        "FUEL": {
            "name": "加油车",
            "code": "FUEL",
            "service_mode": "一对一（ONE_TO_ONE）",
            "base_duration": "20 分钟",
            "crew": "1–2 人",
            "capacity": "5,000–20,000 L",
            "description": (
                "加油车是为飞机提供航空燃油加注服务的特种车辆。"
                "作业期间车辆与飞机一对一绑定，通过软管连接飞机的加油接口进行加注。"
                "加油车需具备防静电、防火花等安全特性，"
                "操作人员需持有相应的危险品操作资质。"
            ),
        },
        "BAG": {
            "name": "行李车",
            "code": "BAG",
            "service_mode": "一对多（ONE_TO_MANY）",
            "base_duration": "15 分钟",
            "crew": "1 人",
            "capacity": "50 件/车",
            "description": (
                "行李车用于在停机位与行李分拣区之间运输旅客行李。"
                "采用一对多服务模式，一辆车可依次服务多个航班。"
                "行李车通常配备拖斗，每个拖斗可装载约 50 件标准行李。"
                "装卸过程需与行李传送带系统配合操作。"
            ),
        },
        "TOW": {
            "name": "牵引车",
            "code": "TOW",
            "service_mode": "一对一（ONE_TO_ONE）",
            "base_duration": "10 分钟",
            "crew": "1 人",
            "capacity": "牵引力 15–30 t",
            "description": (
                "牵引车（也称推车）用于将飞机推离停机位（Pushback）"
                "或牵引飞机在机场区域内移动。"
                "作业期间车辆与飞机一对一绑定，通过牵引杆连接飞机前起落架。"
                "大推力牵引车可拖动 B777 等重型宽体客机。"
            ),
        },
        "STAIR": {
            "name": "客梯车",
            "code": "STAIR",
            "service_mode": "一对一（ONE_TO_ONE）",
            "base_duration": "5 分钟",
            "crew": "1 人",
            "max_height": "3.5–6.5 m",
            "description": (
                "客梯车为旅客提供从航站楼登机口至飞机舱门的上下通道。"
                "车辆升降平台可调节高度以适应不同机型舱门位置。"
                "目前机场客梯车兼容 A320、B737、B777 等主流机型。"
                "作业时需与飞机舱门精确对接，确保旅客通行安全。"
            ),
        },
    }

    type_names = {"FUEL": "加油车", "BAG": "行李车", "TOW": "牵引车", "STAIR": "客梯车"}
    status_names = {
        "IDLE": "空闲", "ASSIGNED": "已分配", "CONFIRMED": "已确认",
        "BUSY": "工作中", "MAINTENANCE": "维修中",
    }

    return render_template(
        "manual.html",
        vtype_info=vtype_info,
        aircraft_rules=aircraft_rules,
        known_aircraft=known_aircraft,
        aircraft_specs=aircraft_specs,
        vehicle_specs=vehicle_specs,
        type_names=type_names,
        status_names=status_names,
    )
