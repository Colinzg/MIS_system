# 机场地面车辆调度系统

## 项目结构

```
MIS_system/
│
├── data/                               # 参考数据（JSON，通过 seed.py 导入数据库）
│   ├── aircraft_catalog.json           #   4 种机型技术参数
│   ├── vehicle_models.json             #   6 种车辆型号技术参数
│   ├── vehicle_inventory.json          #   本机场车辆清单（每台车的静态信息）
│   ├── airport_physical.json           #   机场物理布局：区域、停机位、路网拓扑
│   └── airport_display.json            #   态势图显示坐标
│
├── models/                             # 数据模型
│   ├── __init__.py                     #   db = SQLAlchemy()，统一导入所有模型
│   ├── region.py                       #   Region — 机场区域
│   ├── gate.py                         #   Gate — 停机位（含 has_jet_bridge）
│   ├── vehicle.py                      #   VehicleInfo + VehicleStatus — 车辆静态/动态
│   ├── flight.py                       #   Flight — 航班（关联 gate_id, needs_fuel）
│   ├── task.py                         #   Task — 保障任务（含 depends_on 依赖链）
│   ├── road_network.py                 #   RoadNode, RoadEdge — 路网
│   ├── comm_log.py                     #   CommunicationLog — 调度中心与车载终端通讯
│   └── aircraft.py                     #   AircraftType + AircraftCatalog — 保障规则推导（非DB类）
│
├── services/                           # 业务逻辑（6 个子系统）
│   ├── task_generator.py               #   任务生成 — AircraftType.generate_tasks() → Task
│   ├── scheduler.py                    #   调度规划 — 多约束车辆分配（车型+等级+区域+依赖+容量）
│   ├── path_calculator.py              #   路径计算 — Dijkstra（待实现）
│   ├── vehicle_manager.py              #   车辆管理 — 状态变更、容量回补
│   ├── monitor.py                      #   进度监控 — 超时检测、未分配任务检测
│   └── data_maintenance.py             #   基础数据维护 — CRUD
│
├── routes/                             # Flask 路由
│   ├── __init__.py                     #   蓝图注册
│   ├── dashboard.py                    #   / 和 /dashboard — 调度看板
│   ├── api.py                          #   /api/* — 态势图数据、任务分配、通讯轮询
│   ├── vehicles.py                     #   /vehicles — 车辆状态页
│   ├── schedule.py                     #   /schedule — 调度触发
│   ├── maintenance.py                  #   /maintenance — 数据维护页
│   └── manual.py                       #   /manual — 工作手册（机型/车辆技术参数查询）
│
├── templates/                          # Jinja2 模板
│   ├── base.html                       #   公共布局（导航栏 + Flash 消息）
│   ├── dashboard.html                  #   调度看板（航班列表 + 拖拽分配 + 态势图 + 通讯面板）
│   ├── vehicles.html                   #   车辆状态列表
│   ├── manual.html                     #   工作手册（飞机/车辆技术参数 Wiki）
│   ├── simulator_page.html             #   车载终端模拟器
│   └── maintenance.html                #   数据维护界面
│
├── static/                             # 前端资源
│   ├── style.css                       #   全局样式
│   ├── base.js                         #   公共 JS
│   ├── airport-map.js                  #   D3.js 态势图渲染
│   ├── dashboard-tasks.js              #   任务拖拽分配交互
│   └── dashboard-comm.js               #   车载终端通讯面板
│
├── tests/                              # 单元测试（SQLite 内存数据库）
│   ├── test_task_generator.py          #   任务生成测试
│   ├── test_scheduler.py               #   调度逻辑测试
│   └── test_monitor.py                 #   进度监控测试
│
├── app.py                              # Flask 应用入口（自动启动模拟器）
├── simulator_app.py                    # 车载终端模拟器（独立进程，端口 5001）
├── seed.py                             # 种子数据脚本（从 data/*.json 加载并写入 MySQL）
├── init_db.py                          # 数据库初始化工具（--seed / --reset / --migrate）
├── config.py                           # 应用配置（SECRET_KEY + MySQL 连接串）
└── requirements.txt                    # 依赖：Flask, Flask-SQLAlchemy, PyMySQL
```

## 三层数据架构

| 层 | 介质 | 内容 | 变化频率 |
|---|---|---|---|
| 领域知识库 | `data/*.json` | 飞机/车辆技术参数、机场物理布局 | 月~年 |
| 业务规则 | `models/aircraft.py` | 机型保障规则（由技术参数推导） | 极少 |
| 运行时状态 | MySQL 表 | 航班、车辆、任务、停机位 | 秒~分 |

## 车辆类型（7 种）

| 类型 | 中文名 | 服务模式 | 等级划分 |
|------|--------|---------|---------|
| GPU | 电源车 | 一对一 | 通用型 |
| TOW | 牵引车 | 一对一 | 标准型 / 重型 / 超重型 |
| STAIR | 客梯车 | 一对一 | 标准型 / 高管型 / 超高管型 |
| BUS | 摆渡车 | 一对一 | 小型 / 大型 |
| FUEL | 加油车 | 一对一 | 标准型 / 大容量型 |
| BAG | 行李车 | 一对多 | 通用型 |
| CLEAN | 清洁车 | 一对一 | 通用型 |

## 快速开始

```bash
# 1. 创建数据库
mysql -u root -p -e "CREATE DATABASE airport_scheduling DEFAULT CHARACTER SET utf8mb4;"

# 2. 初始化表结构 + 种子数据
python3 init_db.py --seed

# 3. 启动应用（调度中心 :5000 + 车载模拟器 :5001）
python3 app.py
```
