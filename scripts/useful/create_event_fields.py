#!/usr/bin/env python3
"""
从CSV文件创建事件类型字段结构
1. 创建一级事件类型字段（下拉单选）
2. 为每个一级事件类型创建对应的二三级事件类型字段（展平为二级选项）

使用方法:
    python create_event_fields.py [--api-key API_KEY] [--base-url BASE_URL]

示例:
    python create_event_fields.py
    python create_event_fields.py --api-key af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR
    python create_event_fields.py --base-url http://localhost:8000
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from typing import Dict, List, Any

import requests

# 默认配置
DEFAULT_API_BASE_URL = "http://localhost:9999"
DEFAULT_API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
PAGE_NAME = "用户信息页"
FIELD_GROUP_NAME = "default"

# 主字段配置（一级事件类型字段）
DEFAULT_MAIN_FIELD_NAME = "一级事件类型"
DEFAULT_MAIN_FIELD_LABEL = "一级事件类型"
DEFAULT_MAIN_FIELD_INSTRUCTION = "请选择事件的一级分类"

# 级联字段配置（二三级事件类型字段）
DEFAULT_CASCADE_FIELD_SUFFIX = "二三级事件类型"  # 级联字段后缀
DEFAULT_CASCADE_FIELD_INSTRUCTION_TEMPLATE = "请选择{level1_name}下的二级和三级事件类型"  # 级联字段填写说明模板

# CSV字段名配置 - 可自定义从哪个字段读取数据
DEFAULT_CSV_FIELD_MAPPING = {
    "level1_name": "一级事件类型",
    "level1_id": "一级事件类型ID",
    "level1_instruction": "一级事件类型填写说明",
    "level2_name": "二级事件类型",
    "level2_id": "二级事件类型ID",
    "level2_instruction": "二级事件类型填写说明",
    "level3_name": "三级事件类型",
    "level3_id": "三级事件类型ID",
    "level3_instruction": "三级事件类型填写说明",
}

# ID生成器计数器
_id_counters = {"level1": 0, "level2": 0, "level3": 0}


def generate_id(level: str, parent_id: str = "") -> str:
    """
    自动生成事件类型ID
    level: "level1", "level2", "level3"
    parent_id: 父级ID，用于生成子级ID
    """
    global _id_counters
    _id_counters[level] += 1
    counter = _id_counters[level]

    if level == "level1":
        return f"EVT{counter:03d}"
    elif level == "level2":
        return f"{parent_id}{counter:03d}"
    elif level == "level3":
        return f"{parent_id}{counter:03d}"
    return f"ID{counter}"


def read_csv_data(csv_path: str) -> List[Dict[str, str]]:
    """读取CSV文件数据"""
    data = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data


def get_field_value(row: Dict[str, str], field_mapping: Dict[str, str], key: str, default: str = "") -> str:
    """根据字段映射获取值"""
    csv_field = field_mapping.get(key, DEFAULT_CSV_FIELD_MAPPING.get(key, ""))
    if not csv_field:
        return default
    return row.get(csv_field, default)


def organize_hierarchy(data: List[Dict[str, str]], field_mapping: Dict[str, str] = None) -> Dict:
    """
    组织层级结构
    返回: {
        "一级事件类型1": {
            "id": "EVT001",
            "fill_instruction": "...",
            "二级": {
                "二级事件类型1": {
                    "id": "EVT001001",
                    "三级": {
                        "三级事件类型1": {"id": "EVT001001001", "fill_instruction": "..."},
                        ...
                    }
                },
                ...
            }
        },
        ...
    }
    """
    if field_mapping is None:
        field_mapping = {}

    hierarchy = {}
    # 重置ID计数器
    global _id_counters
    _id_counters = {"level1": 0, "level2": 0, "level3": 0}

    for row in data:
        level1_name = get_field_value(row, field_mapping, "level1_name")
        level1_id = get_field_value(row, field_mapping, "level1_id")
        level1_instruction = get_field_value(row, field_mapping, "level1_instruction")

        level2_name = get_field_value(row, field_mapping, "level2_name")
        level2_id = get_field_value(row, field_mapping, "level2_id")
        level2_instruction = get_field_value(row, field_mapping, "level2_instruction")

        level3_name = get_field_value(row, field_mapping, "level3_name")
        level3_id = get_field_value(row, field_mapping, "level3_id")
        level3_instruction = get_field_value(row, field_mapping, "level3_instruction")

        # 如果没有ID则自动生成
        if not level1_id:
            level1_id = generate_id("level1")

        # 初始化一级事件类型
        if level1_name not in hierarchy:
            hierarchy[level1_name] = {
                "id": level1_id,
                "fill_instruction": level1_instruction,
                "二级": {}
            }

        # 如果没有二级ID则自动生成（基于一级ID）
        if not level2_id:
            level2_id = generate_id("level2", hierarchy[level1_name]["id"])

        # 初始化二级事件类型
        if level2_name not in hierarchy[level1_name]["二级"]:
            hierarchy[level1_name]["二级"][level2_name] = {
                "id": level2_id,
                "fill_instruction": level2_instruction,
                "三级": {}
            }

        # 如果没有三级ID则自动生成（基于二级ID）
        if not level3_id:
            level3_id = generate_id("level3", hierarchy[level1_name]["二级"][level2_name]["id"])

        # 保存三级事件类型
        hierarchy[level1_name]["二级"][level2_name]["三级"][level3_name] = {
            "id": level3_id,
            "fill_instruction": level3_instruction
        }

    return hierarchy


def create_field_group_request(page_name: str, group_name: str, fields: List[Dict]) -> Dict:
    """创建字段组请求体"""
    return {
        "page_name": page_name,
        "group_name": group_name,
        "fields": fields,
        "is_append": False
    }


def create_select_field(
    field_name: str,
    field_label: str,
    options_items: List[Dict],
    fill_instruction: str = ""
) -> Dict:
    """创建下拉单选字段"""
    return {
        "field_name": field_name,
        "field_label": field_label,
        "field_type": "select_single",
        "fill_instruction": fill_instruction,
        "options": {
            "items": options_items,
            "min_selections": 1,
            "max_selections": 1
        }
    }


def build_level1_options(hierarchy: Dict) -> List[Dict]:
    """构建一级事件类型选项列表"""
    options = []
    for level1_name, level1_data in sorted(hierarchy.items(), key=lambda x: x[1]["id"]):
        options.append({
            "label": level1_name,
            "value": level1_data["id"],
            "fill_instruction": level1_data["fill_instruction"]
        })
    return options


def build_flattened_options_for_level1(level1_name: str, level1_data: Dict) -> List[Dict]:
    """
    为特定一级事件类型构建展平的选项列表
    将二级和三级合并：
    - label: "二级名称 - 三级名称"
    - value: "二级ID_三级ID"
    - fill_instruction: 三级填写说明
    """
    items = []

    for level2_name, level2_data in sorted(level1_data["二级"].items(), key=lambda x: x[1]["id"]):
        for level3_name, level3_data in sorted(level2_data["三级"].items(), key=lambda x: x[1]["id"]):
            # 合并名称作为label
            combined_label = f"{level2_name} - {level3_name}"
            # 合并ID作为value
            combined_value = f"{level2_data['id']}_{level3_data['id']}"

            items.append({
                "label": combined_label,
                "value": combined_value,
                "fill_instruction": level3_data["fill_instruction"]
            })

    return items


def send_upsert_request(api_base_url: str, api_key: str, request_data: Dict) -> Dict:
    """发送字段组创建/更新请求"""
    url = f"{api_base_url}/api/autofill/field_group/upsert"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    try:
        response = requests.post(url, json=request_data, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"响应状态码: {e.response.status_code}")
            print(f"响应内容: {e.response.text[:500]}")
        raise


def test_field_creation(api_base_url: str, api_key: str, page_name: str, field_name: str) -> bool:
    """测试字段是否创建成功"""
    url = f"{api_base_url}/api/autofill/field_spec/list"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    params = {
        "page_name": page_name,
        "field_names": [field_name]
    }

    try:
        response = requests.post(url, json=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("data") and len(data["data"]) > 0:
                return True
        return False
    except Exception as e:
        print(f"测试字段失败: {e}")
        return False


def parse_field_mapping(mapping_str: str) -> Dict[str, str]:
    """
    解析字段映射字符串
    格式: key1=value1,key2=value2
    例如: level1_name=一级分类,level1_id=一级ID
    """
    if not mapping_str:
        return {}
    mapping = {}
    for pair in mapping_str.split(","):
        if "=" in pair:
            key, value = pair.split("=", 1)
            mapping[key.strip()] = value.strip()
    return mapping


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="从CSV创建事件类型字段结构")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API Key (默认使用预设值)")
    parser.add_argument("--base-url", default=DEFAULT_API_BASE_URL, help="API基础URL")
    parser.add_argument("--csv-path", default="/Users/lu/code/code/py/autofill/test_csv_data/field_specs_hierarchical_1778329323654.csv",
                        help="CSV文件路径")
    parser.add_argument("--page-name", default=PAGE_NAME, help="页面名称")
    parser.add_argument("--group-name", default=FIELD_GROUP_NAME, help="字段组名称")
    parser.add_argument("--field-mapping", default="",
                        help="CSV字段映射，格式: key1=value1,key2=value2。支持的key: level1_name,level1_id,level1_instruction,level2_name,level2_id,level2_instruction,level3_name,level3_id,level3_instruction")
    parser.add_argument("--auto-generate-id", action="store_true",
                        help="当ID字段为空时自动生成ID")
    # 主字段配置参数
    parser.add_argument("--main-field-name", default=DEFAULT_MAIN_FIELD_NAME,
                        help="主字段名称（一级事件类型字段）")
    parser.add_argument("--main-field-label", default=DEFAULT_MAIN_FIELD_LABEL,
                        help="主字段标签（一级事件类型字段）")
    parser.add_argument("--main-field-instruction", default=DEFAULT_MAIN_FIELD_INSTRUCTION,
                        help="主字段填写说明")
    # 级联字段配置参数
    parser.add_argument("--cascade-field-suffix", default=DEFAULT_CASCADE_FIELD_SUFFIX,
                        help="级联字段后缀名称")
    parser.add_argument("--cascade-field-instruction-template", default=DEFAULT_CASCADE_FIELD_INSTRUCTION_TEMPLATE,
                        help="级联字段填写说明模板，可用{level1_name}作为变量")
    # 只创建主字段选项
    parser.add_argument("--main-only", action="store_true",
                        help="只创建主字段，跳过级联字段创建")
    args = parser.parse_args()

    csv_path = args.csv_path
    api_base_url = args.base_url
    api_key = args.api_key
    page_name = args.page_name
    group_name = args.group_name
    field_mapping = parse_field_mapping(args.field_mapping)
    
    # 字段配置
    main_field_name = args.main_field_name
    main_field_label = args.main_field_label
    main_field_instruction = args.main_field_instruction
    cascade_field_suffix = args.cascade_field_suffix
    cascade_field_instruction_template = args.cascade_field_instruction_template
    main_only = args.main_only

    print("=" * 80)
    print("从CSV创建事件类型字段结构")
    print("=" * 80)
    print(f"API Base URL: {api_base_url}")
    print(f"页面名称: {page_name}")
    print(f"字段组名称: {group_name}")
    print(f"CSV文件: {csv_path}")
    if field_mapping:
        print(f"字段映射: {field_mapping}")
    print(f"主字段名称: {main_field_name}")
    print(f"主字段标签: {main_field_label}")
    print(f"级联字段后缀: {cascade_field_suffix}")
    print(f"只创建主字段: {'是' if main_only else '否'}")
    print("=" * 80)

    # 1. 读取CSV数据
    print(f"\n[1/4] 读取CSV文件...")
    try:
        data = read_csv_data(csv_path)
        print(f"      ✓ 读取到 {len(data)} 行数据")
    except Exception as e:
        print(f"      ✗ 读取CSV失败: {e}")
        sys.exit(1)

    # 2. 组织层级结构
    print("\n[2/4] 组织层级结构...")
    hierarchy = organize_hierarchy(data, field_mapping)
    print(f"      ✓ 一级事件类型数量: {len(hierarchy)}")

    # 统计二级和三级
    level2_count = sum(len(level1["二级"]) for level1 in hierarchy.values())
    level3_count = sum(
        len(level2["三级"])
        for level1 in hierarchy.values()
        for level2 in level1["二级"].values()
    )
    print(f"      ✓ 二级事件类型数量: {level2_count}")
    print(f"      ✓ 三级事件类型数量: {level3_count}")

    # 3. 创建一级事件类型字段（主字段）
    print(f"\n[3/4] 创建主字段 ({main_field_name})...")
    level1_options = build_level1_options(hierarchy)
    print(f"      主字段选项数量: {len(level1_options)}")

    level1_field = create_select_field(
        field_name=main_field_name,
        field_label=main_field_label,
        options_items=level1_options,
        fill_instruction=main_field_instruction
    )

    level1_request = create_field_group_request(
        page_name=page_name,
        group_name=group_name,
        fields=[level1_field]
    )

    print(f"      发送请求创建主字段...")
    try:
        response = send_upsert_request(api_base_url, api_key, level1_request)
        if response.get("code") == 200 or response.get("success"):
            print(f"      ✓ 主字段创建成功")
        else:
            print(f"      ✗ 创建失败: {response.get('message', '未知错误')}")
            sys.exit(1)
    except Exception as e:
        print(f"      ✗ 请求失败: {e}")
        sys.exit(1)

    # 验证主字段创建
    print(f"      验证字段创建...")
    if test_field_creation(api_base_url, api_key, page_name, main_field_name):
        print(f"      ✓ 验证通过")
    else:
        print(f"      ✗ 验证失败，字段可能未正确创建")

    # 4. 为每个一级事件类型创建展平的二三级字段（级联字段）
    success_count = 0
    failed_count = 0

    if main_only:
        print("\n[4/4] 跳过级联字段创建（--main-only 模式）")
    else:
        print(f"\n[4/4] 创建级联字段（后缀: {cascade_field_suffix}）...")

        for level1_name, level1_data in sorted(hierarchy.items(), key=lambda x: x[1]["id"]):
            field_name = f"{level1_name}_{cascade_field_suffix}"
            field_label = f"{level1_name}-的{cascade_field_suffix}"
            fill_instruction = cascade_field_instruction_template.format(level1_name=level1_name)

            print(f"\n      处理: {level1_name}")
            print(f"      字段名称: {field_name}")

            # 构建展平选项
            flattened_options = build_flattened_options_for_level1(level1_name, level1_data)
            print(f"      展平选项数量: {len(flattened_options)}")
            
            # 显示前3个选项示例
            if flattened_options:
                print(f"      选项示例:")
                for i, opt in enumerate(flattened_options[:3]):
                    print(f"        - {opt['label']} ({opt['value']})")
                if len(flattened_options) > 3:
                    print(f"        ... 共 {len(flattened_options)} 个选项")

            # 创建字段
            field = create_select_field(
                field_name=field_name,
                field_label=field_label,
                options_items=flattened_options,
                fill_instruction=fill_instruction
            )

            request = create_field_group_request(
                page_name=page_name,
                group_name=group_name,
                fields=[field]
            )

            print(f"      发送请求创建字段...")
            try:
                response = send_upsert_request(api_base_url, api_key, request)
                if response.get("code") == 200 or response.get("success"):
                    print(f"      ✓ 创建成功")
                    success_count += 1
                else:
                    print(f"      ✗ 创建失败: {response.get('message', '未知错误')}")
                    failed_count += 1
            except Exception as e:
                print(f"      ✗ 请求失败: {e}")
                failed_count += 1

    print("\n" + "=" * 80)
    print("执行结果汇总")
    print("=" * 80)
    print(f"主字段: 1 个 (✓ 成功)")
    if not main_only:
        print(f"级联字段: {success_count} 个成功, {failed_count} 个失败")
        print(f"总计: {success_count + 1} 个字段")
    else:
        print(f"级联字段: 已跳过（--main-only 模式）")
    print("=" * 80)

    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
