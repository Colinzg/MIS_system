"""数据库初始化入口 — 手动运行，不参与应用运行时.

用户手动执行此脚本完成数据库的建表、迁移、重置等操作。
应用启动（app.py）不再执行任何数据库结构修改。

用法:
    python init_db.py               清空数据库并重建所有表
    python init_db.py --seed        清空重建 + 写入种子数据
    python init_db.py --migrate     检查模型与数据库差异并输出 ALTER 语句

建议流程:
    1. 首次部署:  python init_db.py --seed
    2. 模型变更:  python init_db.py --migrate  查看差异，手动执行 ALTER
    3. 开发重置:  python init_db.py --seed
"""
import sys
import argparse

from app import create_app
from models import db


def init(seed_data=False, reset=True):
    """初始化数据库结构。

    Args:
        seed_data: 是否同时写入种子数据
        reset: 是否清空重建（会丢失所有数据），默认 True
    """
    app = create_app()
    with app.app_context():
        if reset:
            db.drop_all()
            print("✓ 已清空所有表")

        db.create_all()
        print("✓ 数据库表结构已就绪")

        if seed_data:
            from seed import seed
            seed()


def check_migration():
    """检查模型与数据库的差异（仅输出建议，不自动执行）。

    SQLAlchemy 的 create_all() 不会为已有表新增列，
    因此当模型增加了新字段（如 Flight.aircraft_type）时，
    需要手动执行 ALTER TABLE。
    """
    app = create_app()
    with app.app_context():
        # 获取所有模型定义的表
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()

        print("=== 模型与数据库差异检查 ===\n")
        for name, table in db.metadata.tables.items():
            if name not in existing_tables:
                print(f"  [新增表] {name} — 运行 python init_db.py 即可创建")
                continue

            # 检查已有表的列差异
            existing_cols = {c["name"] for c in inspector.get_columns(name)}
            model_cols = {c.name for c in table.columns}
            missing = model_cols - existing_cols

            if missing:
                print(f"  [缺列] {name}: 缺少 {', '.join(sorted(missing))}")
                print(f"         请在数据库中执行以下 ALTER 语句：")
                for col_name in sorted(missing):
                    col = table.columns[col_name]
                    col_type = col.type
                    nullable = "NULL" if col.nullable else "NOT NULL"
                    default = f"DEFAULT {col.default.arg}" if col.default else ""
                    print(f"           ALTER TABLE {name} ADD COLUMN {col_name} {col_type} {nullable} {default};".strip())
                print()

        print("=== 检查完毕 ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="机场地面车辆调度系统 — 数据库初始化工具")
    parser.add_argument("--seed", action="store_true", help="清空重建后写入种子数据")
    parser.add_argument("--migrate", action="store_true", help="检查模型与数据库差异")
    args = parser.parse_args()

    if args.migrate:
        check_migration()
    else:
        confirm = input("⚠️  将清空所有数据并重建表结构，确定吗？(yes/no): ")
        if confirm.lower() != "yes":
            print("已取消")
            sys.exit(0)
        init(seed_data=args.seed)
