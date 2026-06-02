"""车辆数据录入与管理工具.

管理两个核心数据文件:
  data/vehicle_models.json    — 车辆型号技术参数（以型号为对象）
  data/vehicle_inventory.json — 机场保有车辆清单（以车辆个体为对象）

用法:
  python scripts/data_entry_vehicles.py list-models          # 列出所有车辆型号
  python scripts/data_entry_vehicles.py list-inventory       # 列出所有保有车辆
  python scripts/data_entry_vehicles.py list-inventory --type TOW --size 小型  # 筛选
  python scripts/data_entry_vehicles.py add-model            # 交互式添加车辆型号
  python scripts/data_entry_vehicles.py add-vehicle          # 交互式添加保有车辆
  python scripts/data_entry_vehicles.py validate             # 校验数据一致性
  python scripts/data_entry_vehicles.py show-types           # 查看车辆类型及大小等级说明
"""
import json
import os
import sys
import argparse
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

VALID_TYPES = ["TOW", "GPU", "STAIR", "BUS", "FUEL", "BAG"]
VALID_SIZE_CLASSES = {
    "TOW":   ["小型", "中型", "大型"],
    "GPU":   ["小型", "大型"],
    "STAIR": ["标准", "高升程"],
    "BUS":   ["大型", "标准"],
    "FUEL":  ["标准"],
    "BAG":   ["标准"],
}
TYPE_NAMES = {
    "TOW": "牵引车", "GPU": "电源车", "STAIR": "客梯车",
    "BUS": "摆渡车", "FUEL": "加油车", "BAG": "行李拖车",
}


def load_json(filename: str) -> list:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        print(f"[错误] 文件不存在: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename: str, data: list):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"[OK] 已保存到 {filename}")


# ── 列出车辆型号 ────────────────────────────────────────────

def cmd_list_models(args):
    catalog = load_json("vehicle_models.json")
    for entry in catalog:
        vt = entry["vehicle_type"]
        print(f"\n{'='*60}")
        print(f"  {vt} — {entry['name']}（服务模式: {entry['service_mode']}）")
        if entry.get("constraints"):
            note = entry["constraints"].get("note", "")
            if note:
                print(f"  约束: {note}")
        print(f"  {'—'*50}")
        for m in entry.get("models", []):
            sc = m.get("size_class", "—")
            mfr = m.get("manufacturer", "—")
            compat = ", ".join(m.get("compatible_aircraft", []))
            dur = m.get("base_duration_min", "—")
            print(f"  {m['brand_model']}")
            print(f"    生产商: {mfr}  |  等级: {sc}  |  适用: {compat}  |  基准时长: {dur}min")
            # 打印其他技术参数
            extra = {k: v for k, v in m.items() if k not in (
                "brand_model", "manufacturer", "size_class",
                "compatible_aircraft", "base_duration_min"
            )}
            if extra:
                extra_str = "  |  ".join(f"{k}: {v}" for k, v in extra.items())
                print(f"    参数: {extra_str}")
        print()


# ── 列出保有车辆 ────────────────────────────────────────────

def cmd_list_inventory(args):
    inventory = load_json("vehicle_inventory.json")

    # 筛选
    items = inventory
    if args.type:
        items = [v for v in items if v["vehicle_type"] == args.type]
    if args.size:
        items = [v for v in items if v.get("size_class") == args.size]

    # 按类型分组
    groups = {}
    for v in items:
        vt = v["vehicle_type"]
        groups.setdefault(vt, []).append(v)

    total = 0
    for vt in VALID_TYPES:
        vehicles = groups.get(vt, [])
        if not vehicles:
            continue
        print(f"\n{'='*60}")
        print(f"  {vt} {TYPE_NAMES.get(vt, '')} — {len(vehicles)} 台")
        print(f"  {'—'*50}")
        for v in vehicles:
            sc = v.get("size_class", "—")
            region = v.get("region", "—")
            remark = v.get("remark", "")
            print(f"  {v['plate_number']}  {v['brand_model']}  [{sc}]  {region}区")
            if remark:
                print(f"    {remark}")
        total += len(vehicles)

    print(f"\n{'='*60}")
    print(f"  总计: {total} 台车辆")


# ── 交互式添加车辆型号 ──────────────────────────────────────

def cmd_add_model(args):
    catalog = load_json("vehicle_models.json")

    print("添加车辆型号\n")
    print("车辆类型: TOW / GPU / STAIR / BUS / FUEL / BAG")
    vt = input("请输入车辆类型: ").strip().upper()
    if vt not in VALID_TYPES:
        print(f"[错误] 无效类型 '{vt}'，可选: {', '.join(VALID_TYPES)}")
        sys.exit(1)

    # 找到对应类型的 entry
    entry = next((e for e in catalog if e["vehicle_type"] == vt), None)
    if not entry:
        print(f"[错误] vehicle_models.json 中不存在的车辆类型: {vt}")
        sys.exit(1)

    print(f"\n当前 {TYPE_NAMES[vt]} 已有型号:")
    for m in entry["models"]:
        print(f"  - {m['brand_model']} [{m.get('size_class', '—')}]")

    print()
    brand = input("品牌型号 (如 '威海广泰 WGQY-20'): ").strip()
    if not brand:
        print("[取消] 未输入型号名称")
        sys.exit(0)

    # 检查重复
    existing = [m["brand_model"] for m in entry["models"]]
    if brand in existing:
        print(f"[错误] 型号 '{brand}' 已存在")
        sys.exit(1)

    mfr = input("生产商: ").strip()

    valid_sizes = VALID_SIZE_CLASSES.get(vt, ["标准"])
    sc = input(f"大小等级 ({'/'.join(valid_sizes)}): ").strip()
    if sc not in valid_sizes:
        print(f"[错误] 无效等级 '{sc}'，{vt} 类型可选: {', '.join(valid_sizes)}")
        sys.exit(1)

    compat = input("适用机型 (用逗号分隔，如 'A320,B737'): ").strip()
    compat_list = [c.strip() for c in compat.split(",") if c.strip()] if compat else []

    dur_str = input("基准服务时长(分钟): ").strip()
    dur = int(dur_str) if dur_str else 15

    new_model = {
        "brand_model": brand,
        "manufacturer": mfr,
        "size_class": sc,
        "compatible_aircraft": compat_list,
        "base_duration_min": dur,
    }

    # 询问是否有额外技术参数
    print("\n可选技术参数（直接回车跳过）:")
    if vt == "TOW":
        val = input("  牵引力(kN): ").strip()
        if val:
            new_model["towing_force_kn"] = int(val)
    elif vt == "GPU":
        val = input("  输出功率(kVA): ").strip()
        if val:
            new_model["power_kva"] = int(val)
    elif vt == "STAIR":
        val = input("  最大工作高度(m): ").strip()
        if val:
            new_model["max_height_m"] = float(val)
    elif vt == "BUS":
        val = input("  载客量(人): ").strip()
        if val:
            new_model["passenger_capacity"] = int(val)
    elif vt == "FUEL":
        val = input("  燃油类型 (如 加油栓车): ").strip()
        if val:
            new_model["fuel_type"] = val
    elif vt == "BAG":
        val = input("  牵引能力(吨): ").strip()
        if val:
            new_model["towing_capacity_t"] = int(val)

    entry["models"].append(new_model)
    save_json("vehicle_models.json", catalog)
    print(f"\n[OK] 已添加型号: {brand} [{sc}]")


# ── 交互式添加保有车辆 ──────────────────────────────────────

def cmd_add_vehicle(args):
    catalog = load_json("vehicle_models.json")
    inventory = load_json("vehicle_inventory.json")

    print("添加机场保有车辆\n")

    # 显示可用的型号
    print("可用车辆型号:")
    model_map = {}
    for entry in catalog:
        for m in entry.get("models", []):
            key = m["brand_model"]
            model_map[key] = {
                "vehicle_type": entry["vehicle_type"],
                "size_class": m.get("size_class"),
            }
            print(f"  [{entry['vehicle_type']}] {key} ({m.get('size_class', '—')})")
    print()

    brand = input("品牌型号 (从上述列表中选择): ").strip()
    if brand not in model_map:
        print(f"[错误] 未知型号 '{brand}'，请先通过 add-model 添加")
        sys.exit(1)

    model_info = model_map[brand]
    vt = model_info["vehicle_type"]
    sc = model_info["size_class"]

    plate = input("车牌号 (如 '民航-B2030'): ").strip()
    if not plate:
        print("[取消] 未输入车牌号")
        sys.exit(0)

    existing = [v["plate_number"] for v in inventory]
    if plate in existing:
        print(f"[错误] 车牌号 '{plate}' 已存在")
        sys.exit(1)

    region = input("所属区域 (A/B): ").strip().upper()
    if region not in ("A", "B"):
        print(f"[警告] 区域通常为 A 或 B，已设为 '{region}'")

    date_str = input("购置日期 (YYYY-MM-DD，直接回车为今天): ").strip()
    if not date_str:
        purchase_date = datetime.now().strftime("%Y-%m-%d")
    else:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            purchase_date = date_str
        except ValueError:
            print("[错误] 日期格式错误，应为 YYYY-MM-DD")
            sys.exit(1)

    asset_tag = input("固定资产标签 (直接回车跳过): ").strip()
    remark = input("备注 (如 'B区备用牵引'): ").strip()

    new_vehicle = {
        "plate_number": plate,
        "vehicle_type": vt,
        "brand_model": brand,
        "size_class": sc,
        "region": region,
        "purchase_date": purchase_date,
    }
    if asset_tag:
        new_vehicle["asset_tag"] = asset_tag
    if remark:
        new_vehicle["remark"] = remark

    inventory.append(new_vehicle)
    save_json("vehicle_inventory.json", inventory)
    print(f"\n[OK] 已添加车辆: {plate} ({brand}, {sc}, {region}区)")

    # 统计
    type_count = {}
    for v in inventory:
        type_count[v["vehicle_type"]] = type_count.get(v["vehicle_type"], 0) + 1
    print(f"当前保有: {len(inventory)} 台 — {', '.join(f'{TYPE_NAMES[t]}{c}台' for t, c in sorted(type_count.items()))}")


# ── 数据校验 ────────────────────────────────────────────────

def cmd_validate(args):
    catalog = load_json("vehicle_models.json")
    inventory = load_json("vehicle_inventory.json")
    errors = []
    warnings = []

    # 从 catalog 建立 brand_model → info 的索引
    model_index = {}
    for entry in catalog:
        for m in entry.get("models", []):
            key = m["brand_model"]
            if key in model_index:
                errors.append(f"型号重复: '{key}' 在 vehicle_models.json 中出现多次")
            model_index[key] = {
                "vehicle_type": entry["vehicle_type"],
                "size_class": m.get("size_class"),
                "compatible_aircraft": m.get("compatible_aircraft", []),
            }

    # 校验 inventory 每台车
    seen_plates = set()
    for v in inventory:
        plate = v.get("plate_number", "")
        if not plate:
            errors.append("存在空车牌号的车辆记录")
            continue
        if plate in seen_plates:
            errors.append(f"车牌号重复: {plate}")
        seen_plates.add(plate)

        vt = v.get("vehicle_type", "")
        if vt not in VALID_TYPES:
            errors.append(f"{plate}: 无效的 vehicle_type '{vt}'")

        brand = v.get("brand_model", "")
        if not brand:
            errors.append(f"{plate}: 缺少 brand_model")
            continue

        if brand not in model_index:
            warnings.append(f"{plate}: 型号 '{brand}' 在 vehicle_models.json 中不存在")
            continue

        model = model_index[brand]
        if model["vehicle_type"] != vt:
            errors.append(
                f"{plate}: vehicle_type='{vt}' 与 vehicle_models.json 中"
                f" '{brand}' 的 vehicle_type='{model['vehicle_type']}' 不一致"
            )

        expected_sc = model["size_class"]
        actual_sc = v.get("size_class")
        if expected_sc and actual_sc and expected_sc != actual_sc:
            warnings.append(
                f"{plate}: size_class='{actual_sc}' 与 vehicle_models.json 中"
                f" '{brand}' 的 size_class='{expected_sc}' 不一致"
            )

    # 统计
    type_count = {}
    for v in inventory:
        type_count[v["vehicle_type"]] = type_count.get(v["vehicle_type"], 0) + 1

    print(f"\n{'='*60}")
    print(f"数据校验报告")
    print(f"  车辆型号: {len(model_index)} 种")
    print(f"  保有车辆: {len(inventory)} 台")
    print(f"  错误: {len(errors)}")
    print(f"  警告: {len(warnings)}")
    print()

    if errors:
        print("❌ 错误:")
        for e in errors:
            print(f"  - {e}")

    if warnings:
        print("⚠️  警告:")
        for w in warnings:
            print(f"  - {w}")

    if not errors and not warnings:
        print("✅ 所有数据校验通过！")

    print()
    print("保有车辆按类型统计:")
    for vt in VALID_TYPES:
        count = type_count.get(vt, 0)
        if count:
            print(f"  {vt} {TYPE_NAMES[vt]}: {count} 台")

    if errors:
        print("\n请修复以上错误后再重新导入 seed.py。")


# ── 查看类型说明 ────────────────────────────────────────────

def cmd_show_types(args):
    print("\n车辆类型与大小等级说明:\n")
    for vt in VALID_TYPES:
        sizes = VALID_SIZE_CLASSES.get(vt, [])
        print(f"  {vt} — {TYPE_NAMES[vt]}")
        print(f"    大小等级: {', '.join(sizes)}")
        if vt == "TOW":
            print(f"    小型 120-160kN / 中型 180-240kN / 大型 300-400kN")
        elif vt == "GPU":
            print(f"    小型 90kVA / 大型 140kVA")
        elif vt == "STAIR":
            print(f"    标准 4.4m / 高升程 5.8m+")
        elif vt == "BUS":
            print(f"    大型 100人+ / 标准 50人+")
        print()


# ── CLI 入口 ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="机场地面车辆数据录入与管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/data_entry_vehicles.py list-models
  python scripts/data_entry_vehicles.py list-inventory --type TOW
  python scripts/data_entry_vehicles.py add-model
  python scripts/data_entry_vehicles.py add-vehicle
  python scripts/data_entry_vehicles.py validate
  python scripts/data_entry_vehicles.py show-types
        """,
    )
    subparsers = parser.add_subparsers(dest="command")

    p = subparsers.add_parser("list-models", help="列出所有车辆型号")
    p = subparsers.add_parser("list-inventory", help="列出所有保有车辆")
    p.add_argument("--type", help="按车辆类型筛选 (TOW/GPU/STAIR/BUS/FUEL/BAG)")
    p.add_argument("--size", help="按大小等级筛选 (小型/中型/大型/标准/高升程)")

    subparsers.add_parser("add-model", help="交互式添加车辆型号")
    subparsers.add_parser("add-vehicle", help="交互式添加保有车辆")
    subparsers.add_parser("validate", help="校验 vehicle_models.json 与 vehicle_inventory.json 的数据一致性")
    subparsers.add_parser("show-types", help="查看车辆类型及大小等级说明")

    args = parser.parse_args()

    commands = {
        "list-models":    cmd_list_models,
        "list-inventory": cmd_list_inventory,
        "add-model":      cmd_add_model,
        "add-vehicle":    cmd_add_vehicle,
        "validate":       cmd_validate,
        "show-types":     cmd_show_types,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()
        # 默认显示类型说明
        cmd_show_types(args)


if __name__ == "__main__":
    main()
