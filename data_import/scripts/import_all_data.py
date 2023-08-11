#!/usr/bin/env python3
"""
导入所有关键数据到系统
1. 导入事件类型字段（级联字段）
2. 导入400电话字段选项
3. 导入模板字段
4. 创建服务记录类型字段和字段组

使用方法:
    python import_all_data.py [--api-key API_KEY] [--base-url BASE_URL]

示例:
    python import_all_data.py
    python import_all_data.py --api-key af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR
"""

import argparse
import csv
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

import requests

# 默认配置
DEFAULT_API_BASE_URL = "http://localhost:9999"
DEFAULT_API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
PAGE_NAME = "话务工作台"
APP_NAME = "test_app"  # 默认应用名称

# 文件路径 - 相对于脚本所在目录
_script_dir = Path(__file__).parent.parent
DATA_DIR = _script_dir / "data"

# CSV文件路径
EVENT_TYPES_CSV = DATA_DIR / "event_types.csv"
PHONE_FIELD_OPTIONS_CSV = DATA_DIR / "phone_field_options.csv"
TEMPLATE_FIELDS_CSV = DATA_DIR / "template_fields.csv"
TEMPLATES_EXPORT_CSV = DATA_DIR / "templates_export.csv"


def send_request(api_base_url: str, api_key: str, endpoint: str, data: Dict = None, method: str = "POST") -> Dict:
    """发送API请求"""
    url = f"{api_base_url}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    try:
        if method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=30)
        elif method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            raise ValueError(f"不支持的HTTP方法: {method}")

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"响应状态码: {e.response.status_code}")
            print(f"响应内容: {e.response.text[:500]}")
        raise


def read_csv_data(csv_path: Path) -> List[Dict[str, str]]:
    """读取CSV文件数据"""
    data = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data


# ============ 1. 导入事件类型字段 ============

def import_event_types(api_base_url: str, api_key: str, page_name: str) -> bool:
    """导入事件类型字段（级联字段）"""
    print("\n" + "=" * 60)
    print("[1/4] 导入事件类型字段")
    print("=" * 60)

    csv_data = read_csv_data(EVENT_TYPES_CSV)
    print(f"读取了 {len(csv_data)} 行事件类型数据")

    # 组织层级数据
    hierarchy = defaultdict(lambda: {"children": defaultdict(lambda: {"children": {}})})

    for row in csv_data:
        level1_name = row.get("一级事件类型", "").strip()
        level1_id = row.get("一级事件类型ID", "").strip()
        level1_instruction = row.get("一级事件类型填写说明", "").strip()

        level2_name = row.get("二级事件类型", "").strip()
        level2_id = row.get("二级事件类型ID", "").strip()
        level2_instruction = row.get("二级事件类型填写说明", "").strip()

        level3_name = row.get("三级事件类型", "").strip()
        level3_id = row.get("三级事件类型ID", "").strip()
        level3_instruction = row.get("三级事件类型填写说明", "").strip()

        if not level1_name:
            continue

        # 初始化一级
        if level1_name not in hierarchy:
            hierarchy[level1_name] = {
                "id": level1_id,
                "instruction": level1_instruction,
                "children": {}
            }

        # 初始化二级
        if level2_name and level2_name not in hierarchy[level1_name]["children"]:
            hierarchy[level1_name]["children"][level2_name] = {
                "id": level2_id,
                "instruction": level2_instruction,
                "children": {}
            }

        # 初始化三级
        if level3_name and level2_name:
            hierarchy[level1_name]["children"][level2_name]["children"][level3_name] = {
                "id": level3_id,
                "instruction": level3_instruction
            }

    # 构建主字段选项（一级事件类型）
    main_options = []
    for name, data in hierarchy.items():
        main_options.append({
            "label": name,
            "value": data["id"],
            "fill_instruction": data["instruction"]
        })

    print(f"主字段选项数: {len(main_options)}")

    # 创建主字段
    main_field = {
        "field_name": "一级事件类型",
        "field_label": "一级事件类型",
        "field_type": "select_single",
        "fill_instruction": "请选择一级事件类型",
        "options": {
            "items": main_options,
            "min_selections": 1,
            "max_selections": 1
        }
    }

    # 创建次字段（为每个一级事件类型创建级联字段）
    secondary_fields = []
    for level1_name, level1_data in hierarchy.items():
        secondary_options = []
        for level2_name, level2_data in level1_data["children"].items():
            for level3_name, level3_data in level2_data["children"].items():
                combined_name = f"{level2_name}-{level3_name}"
                combined_id = f"{level2_data['id']}_{level3_data['id']}"
                combined_instruction = f"{level2_data['instruction']}\n{level3_data['instruction']}".strip()

                secondary_options.append({
                    "label": combined_name,
                    "value": combined_id,
                    "fill_instruction": combined_instruction
                })

        if secondary_options:
            secondary_field_name = f"{level1_name}-二三级事件类型"
            secondary_field = {
                "field_name": secondary_field_name,
                "field_label": secondary_field_name,
                "field_type": "select_single",
                "fill_instruction": f"请选择{level1_name}的详细分类",
                "options": {
                    "items": secondary_options,
                    "min_selections": 1,
                    "max_selections": 1
                }
            }
            secondary_fields.append(secondary_field)

    print(f"次字段数量: {len(secondary_fields)}")

    # 创建字段组
    fields = [main_field] + secondary_fields
    print(f"字段总数: {len(fields)}")

    try:
        # 先创建主字段
        print("\n创建主字段...")
        result = send_request(
            api_base_url, api_key,
            "/api/autofill/field_group/upsert",
            {
                "page_name": page_name,
                "group_name": "事件类型",
                "fields": [main_field],
                "is_append": False
            }
        )
        print(f"主字段创建成功: {result.get('msg', 'OK')}")

        # 分批创建次字段
        if secondary_fields:
            print("\n创建次字段...")
            batch_size = 5
            for i in range(0, len(secondary_fields), batch_size):
                batch = secondary_fields[i:i+batch_size]
                print(f"  批次 {i//batch_size + 1}/{(len(secondary_fields)-1)//batch_size + 1} ({len(batch)}个字段)...")
                result = send_request(
                    api_base_url, api_key,
                    "/api/autofill/field_group/upsert",
                    {
                        "page_name": page_name,
                        "group_name": "事件类型",
                        "fields": batch,
                        "is_append": True
                    }
                )
                time.sleep(0.5)
            print("次字段创建成功!")

        return True
    except Exception as e:
        print(f"创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============ 2. 导入400电话字段选项 ============

def import_phone_field_options(api_base_url: str, api_key: str, page_name: str) -> bool:
    """导入400电话字段选项"""
    print("\n" + "=" * 60)
    print("[2/4] 导入400电话字段选项")
    print("=" * 60)

    csv_data = read_csv_data(PHONE_FIELD_OPTIONS_CSV)
    print(f"读取了 {len(csv_data)} 行电话字段选项数据")

    # 按字段ID分组
    field_groups = defaultdict(list)
    for row in csv_data:
        field_id = row.get("字段ID", "").strip()
        field_name = row.get("字段名", "").strip()
        option_value = row.get("选项值", "").strip()
        option_label = row.get("选项标签", "").strip()
        instruction = row.get("填写说明", "").strip()

        if field_name and option_value:
            field_groups[field_name].append({
                "label": option_label or option_value,
                "value": option_value,
                "fill_instruction": instruction
            })

    print(f"发现 {len(field_groups)} 个字段")

    # 创建字段
    fields = []
    for field_name, options in field_groups.items():
        field = {
            "field_name": field_name,
            "field_label": field_name,
            "field_type": "select_single",
            "fill_instruction": "请选择",
            "options": {
                "items": options,
                "min_selections": 1,
                "max_selections": 1
            }
        }
        fields.append(field)
        print(f"  字段 '{field_name}': {len(options)} 个选项")

    try:
        print("\n创建字段组...")
        result = send_request(
            api_base_url, api_key,
            "/api/autofill/field_group/upsert",
            {
                "page_name": page_name,
                "group_name": "400电话字段",
                "fields": fields,
                "is_append": False
            }
        )
        print(f"字段组创建成功: {result.get('msg', 'OK')}")
        return True
    except Exception as e:
        print(f"创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============ 3. 导入模板字段 ============

def import_template_fields(api_base_url: str, api_key: str, page_name: str) -> bool:
    """导入模板字段"""
    print("\n" + "=" * 60)
    print("[3/4] 导入模板字段")
    print("=" * 60)

    csv_data = read_csv_data(TEMPLATE_FIELDS_CSV)
    print(f"读取了 {len(csv_data)} 行模板字段数据")

    # 去重字段
    seen_fields = set()
    fields = []

    for row in csv_data:
        field_name = row.get("字段名", "").strip()
        field_label = row.get("字段标签", "").strip()
        instruction = row.get("填写说明", "").strip()

        if not field_name or field_name in seen_fields:
            continue

        seen_fields.add(field_name)

        field = {
            "field_name": field_name,
            "field_label": field_label or field_name,
            "field_type": "text",
            "fill_instruction": instruction
        }
        fields.append(field)

    print(f"去重后字段数: {len(fields)}")

    try:
        print("\n创建字段组...")
        result = send_request(
            api_base_url, api_key,
            "/api/autofill/field_group/upsert",
            {
                "page_name": page_name,
                "group_name": "模板字段",
                "fields": fields,
                "is_append": False
            }
        )
        print(f"字段组创建成功: {result.get('msg', 'OK')}")
        return True
    except Exception as e:
        print(f"创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============ 4. 创建服务记录类型字段和字段组 ============

def extract_variables(template_content: str) -> List[str]:
    """从模板内容中提取变量名 ${variable} -> variable"""
    pattern = r'\$\{([^}]+)\}'
    matches = re.findall(pattern, template_content)
    return list(set(matches))  # 去重


def import_service_record_structure(api_base_url: str, api_key: str, page_name: str) -> bool:
    """创建服务记录类型字段和字段组"""
    print("\n" + "=" * 60)
    print("[4/4] 创建服务记录类型字段和字段组")
    print("=" * 60)

    # 读取模板数据
    templates_data = read_csv_data(TEMPLATES_EXPORT_CSV)
    print(f"读取了 {len(templates_data)} 个模板")

    # 读取字段数据
    fields_data = read_csv_data(TEMPLATE_FIELDS_CSV)
    field_info = {}
    for row in fields_data:
        field_name = row.get("字段名", "").strip()
        field_label = row.get("字段标签", "").strip()
        instruction = row.get("填写说明", "").strip()
        if field_name:
            field_info[field_name] = {
                "label": field_label or field_name,
                "instruction": instruction
            }

    # 创建服务记录类型字段（下拉单选）
    service_type_options = []
    for template in templates_data:
        template_id = template.get("id", "").strip()
        template_name = template.get("name", "").strip()
        summary = template.get("summary", "").strip()

        if template_name:
            service_type_options.append({
                "label": template_name,
                "value": template_id,
                "fill_instruction": summary
            })

    print(f"服务记录类型选项数: {len(service_type_options)}")

    # 创建服务记录类型字段
    service_type_field = {
        "field_name": "服务记录类型",
        "field_label": "服务记录类型",
        "field_type": "select_single",
        "fill_instruction": "请选择服务记录类型",
        "options": {
            "items": service_type_options,
            "min_selections": 1,
            "max_selections": 1
        }
    }

    try:
        # 创建服务记录类型字段组
        print("\n创建服务记录类型字段组...")
        result = send_request(
            api_base_url, api_key,
            "/api/autofill/field_group/upsert",
            {
                "page_name": page_name,
                "group_name": "服务记录类型",
                "fields": [service_type_field],
                "is_append": False
            }
        )
        print(f"服务记录类型字段组创建成功: {result.get('msg', 'OK')}")

        # 为每个模板创建字段组
        print("\n为每个模板创建字段组...")
        for template in templates_data:
            template_name = template.get("name", "").strip()
            template_content = template.get("template_content", "").strip()

            if not template_name or not template_content:
                continue

            # 提取模板中的变量
            variables = extract_variables(template_content)

            if not variables:
                print(f"  模板 '{template_name}': 无变量，跳过")
                continue

            # 构建字段列表
            fields = []
            for var_name in variables:
                info = field_info.get(var_name, {})
                field = {
                    "field_name": var_name,
                    "field_label": info.get("label", var_name),
                    "field_type": "text",
                    "fill_instruction": info.get("instruction", f"请填写{var_name}")
                }
                fields.append(field)

            group_name = f"服务记录-{template_name}"

            print(f"  创建字段组 '{group_name}': {len(fields)} 个字段")

            result = send_request(
                api_base_url, api_key,
                "/api/autofill/field_group/upsert",
                {
                    "page_name": page_name,
                    "group_name": group_name,
                    "fields": fields,
                    "is_append": False
                }
            )

            time.sleep(0.3)

        print("所有模板字段组创建成功!")
        return True

    except Exception as e:
        print(f"创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============ 创建页面 ============

def create_page(api_base_url: str, api_key: str, page_name: str, app_name: str) -> bool:
    """创建页面"""
    print("\n" + "=" * 60)
    print("[0/4] 创建页面")
    print("=" * 60)
    print(f"页面名称: {page_name}")
    print(f"应用名称: {app_name}")

    try:
        result = send_request(
            api_base_url, api_key,
            "/api/v1/autofill/page/create",
            {
                "page_name": page_name,
                "app_name": app_name,
                "description": f"{page_name} - 自动创建"
            }
        )
        print(f"页面创建成功: {result.get('msg', 'OK')}")
        return True
    except Exception as e:
        error_msg = str(e)
        if "already exists" in error_msg or "已存在" in error_msg:
            print(f"页面已存在，跳过创建")
            return True
        print(f"页面创建失败: {e}")
        return False


# ============ 主函数 ============

def main():
    parser = argparse.ArgumentParser(
        description="导入所有关键数据到系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python import_all_data.py
    python import_all_data.py --api-key af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR
    python import_all_data.py --base-url http://localhost:9999
    python import_all_data.py --app-name test_app
        """
    )
    parser.add_argument(
        "--api-key",
        default=DEFAULT_API_KEY,
        help=f"API Key (默认: {DEFAULT_API_KEY[:10]}...)"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_API_BASE_URL,
        help=f"API基础URL (默认: {DEFAULT_API_BASE_URL})"
    )
    parser.add_argument(
        "--page-name",
        default=PAGE_NAME,
        help=f"页面名称 (默认: {PAGE_NAME})"
    )
    parser.add_argument(
        "--app-name",
        default=APP_NAME,
        help=f"应用名称 (默认: {APP_NAME})"
    )
    parser.add_argument(
        "--skip-event-types",
        action="store_true",
        help="跳过导入事件类型"
    )
    parser.add_argument(
        "--skip-phone-fields",
        action="store_true",
        help="跳过导入400电话字段"
    )
    parser.add_argument(
        "--skip-template-fields",
        action="store_true",
        help="跳过导入模板字段"
    )
    parser.add_argument(
        "--skip-service-record",
        action="store_true",
        help="跳过创建服务记录类型"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("数据导入脚本")
    print("=" * 60)
    print(f"API基础URL: {args.base_url}")
    print(f"页面名称: {args.page_name}")

    success_count = 0
    total_count = 0

    # 1. 导入事件类型
    if not args.skip_event_types:
        total_count += 1
        if import_event_types(args.base_url, args.api_key, args.page_name):
            success_count += 1

    # 2. 导入400电话字段
    if not args.skip_phone_fields:
        total_count += 1
        if import_phone_field_options(args.base_url, args.api_key, args.page_name):
            success_count += 1

    # 3. 导入模板字段
    if not args.skip_template_fields:
        total_count += 1
        if import_template_fields(args.base_url, args.api_key, args.page_name):
            success_count += 1

    # 4. 创建服务记录类型
    if not args.skip_service_record:
        total_count += 1
        if import_service_record_structure(args.base_url, args.api_key, args.page_name):
            success_count += 1

    print("\n" + "=" * 60)
    print("导入完成!")
    print(f"成功: {success_count}/{total_count}")
    print("=" * 60)

    sys.exit(0 if success_count == total_count else 1)


if __name__ == "__main__":
    main()
