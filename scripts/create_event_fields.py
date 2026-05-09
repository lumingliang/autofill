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


def read_csv_data(csv_path: str) -> List[Dict[str, str]]:
    """读取CSV文件数据"""
    data = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data


def organize_hierarchy(data: List[Dict[str, str]]) -> Dict:
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
    hierarchy = {}

    for row in data:
        level1_name = row["一级事件类型"]
        level1_id = row["一级事件类型ID"]
        level1_instruction = row.get("一级事件类型填写说明", "")

        level2_name = row["二级事件类型"]
        level2_id = row["二级事件类型ID"]

        level3_name = row["三级事件类型"]
        level3_id = row["三级事件类型ID"]
        level3_instruction = row.get("三级事件类型填写说明", "")

        # 初始化一级事件类型
        if level1_name not in hierarchy:
            hierarchy[level1_name] = {
                "id": level1_id,
                "fill_instruction": level1_instruction,
                "二级": {}
            }

        # 初始化二级事件类型
        if level2_name not in hierarchy[level1_name]["二级"]:
            hierarchy[level1_name]["二级"][level2_name] = {
                "id": level2_id,
                "三级": {}
            }

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


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="从CSV创建事件类型字段结构")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API Key (默认使用预设值)")
    parser.add_argument("--base-url", default=DEFAULT_API_BASE_URL, help="API基础URL")
    parser.add_argument("--csv-path", default="/Users/lu/code/code/py/autofill/test_csv_data/field_specs_hierarchical_1778329323654.csv",
                        help="CSV文件路径")
    parser.add_argument("--page-name", default=PAGE_NAME, help="页面名称")
    parser.add_argument("--group-name", default=FIELD_GROUP_NAME, help="字段组名称")
    args = parser.parse_args()

    csv_path = args.csv_path
    api_base_url = args.base_url
    api_key = args.api_key
    page_name = args.page_name
    group_name = args.group_name

    print("=" * 80)
    print("从CSV创建事件类型字段结构")
    print("=" * 80)
    print(f"API Base URL: {api_base_url}")
    print(f"页面名称: {page_name}")
    print(f"字段组名称: {group_name}")
    print(f"CSV文件: {csv_path}")
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
    hierarchy = organize_hierarchy(data)
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

    # 3. 创建一级事件类型字段
    print("\n[3/4] 创建一级事件类型字段...")
    level1_options = build_level1_options(hierarchy)
    print(f"      一级事件类型选项数量: {len(level1_options)}")

    level1_field = create_select_field(
        field_name="一级事件类型",
        field_label="一级事件类型",
        options_items=level1_options,
        fill_instruction="请选择事件的一级分类"
    )

    level1_request = create_field_group_request(
        page_name=page_name,
        group_name=group_name,
        fields=[level1_field]
    )

    print(f"      发送请求创建一级事件类型字段...")
    try:
        response = send_upsert_request(api_base_url, api_key, level1_request)
        if response.get("code") == 200 or response.get("success"):
            print(f"      ✓ 一级事件类型字段创建成功")
        else:
            print(f"      ✗ 创建失败: {response.get('message', '未知错误')}")
            sys.exit(1)
    except Exception as e:
        print(f"      ✗ 请求失败: {e}")
        sys.exit(1)

    # 验证一级字段创建
    print(f"      验证字段创建...")
    if test_field_creation(api_base_url, api_key, page_name, "一级事件类型"):
        print(f"      ✓ 验证通过")
    else:
        print(f"      ✗ 验证失败，字段可能未正确创建")

    # 4. 为每个一级事件类型创建展平的二三级字段
    print("\n[4/4] 创建二三级事件类型展平字段...")

    success_count = 0
    failed_count = 0

    for level1_name, level1_data in sorted(hierarchy.items(), key=lambda x: x[1]["id"]):
        field_name = f"{level1_name}_二三级事件类型"
        field_label = f"{level1_name} - 二三级事件类型"

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
            fill_instruction=f"请选择{level1_name}下的二级和三级事件类型"
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
    print(f"一级事件类型字段: 1 个 (✓ 成功)")
    print(f"二三级展平字段: {success_count} 个成功, {failed_count} 个失败")
    print(f"总计: {success_count + 1} 个字段")
    print("=" * 80)

    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
