 config.py — 应用配置

  当前只做了一件事：定义 MySQL 连接字符串和密钥。没有其他配置逻辑。

  ---
  app.py — Flask 入口 + 路由

  注册了 3 个路由：

  ┌───────────────────────┬────────────────────────────────────────────────────────┐
  │         路由          │                          功能                          │
  ├───────────────────────┼────────────────────────────────────────────────────────┤
  │ / 和 /dashboard       │ 查所有航班（按时间排序）+ 最近 50 条任务，渲染看板页面 │
  ├───────────────────────┼────────────────────────────────────────────────────────┤
  │ /vehicles             │ 查所有车辆（按车型、车牌排序），渲染车辆状态页         │
  ├───────────────────────┼────────────────────────────────────────────────────────┤
  │ /schedule/<flight_id> │ 调用 Scheduler 为指定航班分配车辆，然后重定向回看板    │
  └───────────────────────┴────────────────────────────────────────────────────────┘

  启动时自动调用 db.create_all() 建表，没有其他初始化逻辑。

  ---
  models/ 数据模型

  region.py — 2 个字段：code（区域代码）+ name（区域名称）。一对多关联 Vehicle 和 Flight。没有地理坐标信息。

  vehicle.py — 4 个字段：plate（车牌）、type（车型）、status（状态）、region_id（所在区域）。一对多关联 Task。没有
  attributes JSON 字段，没有机型适配方法。

  flight.py — 7 个字段：flight_no（航班号）、airline（航司）、scheduled_at（计划时间）、gate（登机口）、region_id、statu
  s、created_at。没有 aircraft_type 字段。

  task.py — 6 个字段：flight_id、vehicle_id、task_type、scheduled_start/end、status。没有 depends_on（前置依赖）字段。

  __init__.py — 初始化 db = SQLAlchemy() 并导入所有模型。

  ---
  services/scheduler.py — 调度算法

  当前实现了最简单的三步逻辑：

  1. 查指定航班下所有 PENDING 且 vehicle_id IS NULL 的任务
  2. 对每个任务，调用 _select_vehicle：
    - 第一步：找同区域 + 同车型 + IDLE 的车，有就返回
    - 第二步：找不到就放宽区域限制，找任意区域 + 同车型 + IDLE 的车
  3. 找到车 → 任务状态改为 IN_PROGRESS，车状态改为 BUSY；找不到 → 记一条错误
  4. 全部处理完后 commit

  没有的东西：机型适配检查、服务模式检查（ONE_TO_ONE/ONE_TO_MANY）、任务依赖顺序、空闲时间最久优先（只是取了第一条）。

  ---
  seed.py — 种子数据

  跑一次会清空数据库重建，然后插入固定数据：
  - 3 个区域（A01 1号航站楼东侧 / B02 2号航站楼西侧 / C03 货运区）
  - 9 辆车（加油车 2、行李车 3、牵引车 2、客梯车 2），全是 IDLE 状态
  - 6 个航班（CA1234、MU2567、CZ3890、3U8888、HU7205、ZH9102），全是 SCHEDULED 状态
  - 每个航班生成 4 个 PENDING 任务（FUEL/BAG/TOW/STAIR 各一个），全是未分配车辆状态

  没有 Aircraft_Resource 数据，任务类型硬编码为这 4 种，跟机型无关。

  ---
  templates/ 页面模板

  base.html — 导航栏（两个链接：调度看板、车辆状态）+ Flash 消息区域 + content 占位。没有登录功能。

  dashboard.html — 两个表格：
  - 航班表格：航班号、航司、时间、区域、状态、调度按钮
  - 任务表格：任务ID、航班、类型、车辆、状态
  - 点击"调度"按钮 → 调 /schedule/<flight_id> 接口

  没有：甘特图、筛选、搜索、分页。

  vehicles.html — 一个表格：车牌、车型（转中文显示）、状态、所在区域。没有：地图、区域筛选、维保记录。

  ---
  static/style.css — 样式

  导航栏深蓝底白字、表格带阴影和圆角、状态徽章按颜色区分（待办蓝/完成绿/失败红/进行中紫）、Flash
  消息、按钮样式。没有响应式布局。

  ---
  tests/test_scheduler.py — 单元测试

  2 个测试用例：
  1. test_schedule_returns_dict — 插入一条最小数据，调 schedule_for_flight，检查返回 dict 且包含 tasks 键
  2. test_schedule_nonexistent_flight — 调不存在的航班 ID，检查是否抛 ValueError

  用 SQLite 内存数据库跑测试，不依赖 MySQL。

  ---
  requirements.txt — 依赖

  三个包：Flask==3.1.0、Flask-SQLAlchemy==3.1.1、PyMySQL==1.1.1