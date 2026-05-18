#!/usr/bin/env python3
"""
创建服务记录类型字段结构和字段组
1. 创建"服务记录类型"字段（下拉单选），选项为各个模板
2. 为每个模板创建字段组，绑定模板中使用的字段
3. 设置字段组的输出模板

使用方法:
    python create_service_record_structure.py [--api-key API_KEY] [--base-url BASE_URL]

示例:
    python create_service_record_structure.py
    python create_service_record_structure.py --api-key af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR
"""

import argparse
import csv
import json
import re
import sys
from typing import Dict, List, Any, Set

import requests

# 默认配置
DEFAULT_API_BASE_URL = "http://localhost:9999"
DEFAULT_API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
PAGE_NAME = "话务工作台"

# 文件路径 - 相对于脚本所在目录
from pathlib import Path
_script_dir = Path(__file__).parent
DEFAULT_TEMPLATES_CSV = str(_script_dir / "data" / "templates_export.csv")
DEFAULT_FIELDS_CSV = str(_script_dir / "data" / "template_fields.csv")
FIELD_GROUP_NAME = "default"


def read_csv_data(csv_path: str) -> List[Dict[str, str]]:
    """读取CSV文件数据"""
    data = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data


def extract_variables(template_content: str) -> List[str]:
    """从模板内容中提取变量名 ${variable} -> variable"""
    pattern = r'\$\{([^}]+)\}'
    variables = re.findall(pattern, template_content)
    return list(set(variables))  # 去重


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


def create_text_field(
    field_name: str,
    field_label: str,
    fill_instruction: str = ""
) -> Dict:
    """创建文本输入字段"""
    return {
        "field_name": field_name,
        "field_label": field_label,
        "field_type": "text",
        "fill_instruction": fill_instruction
    }


def build_service_record_type_options(templates: List[Dict]) -> List[Dict]:
    """构建服务记录类型选项列表"""
    options = []
    for template in templates:
        template_id = template.get("id", "")
        template_name = template.get("name", "")
        summary = template.get("summary", "")
        
        if template_id and template_name:
            options.append({
                "label": template_name,
                "value": str(template_id),
                "fill_instruction": summary
            })
    return options


def get_field_label(field_name: str, fields_data: List[Dict]) -> str:
    """根据字段名获取字段标签"""
    for field in fields_data:
        if field.get("字段名") == field_name:
            return field.get("字段标签", field_name)
    return field_name


def get_field_instruction(field_name: str, fields_data: List[Dict]) -> str:
    """根据字段名获取填写说明"""
    for field in fields_data:
        if field.get("字段名") == field_name:
            return field.get("填写说明", "")
    return ""


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="创建服务记录类型字段结构")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API Key")
    parser.add_argument("--base-url", default=DEFAULT_API_BASE_URL, help="API基础URL")
    parser.add_argument("--templates-csv", default=DEFAULT_TEMPLATES_CSV, help="模板CSV文件路径")
    parser.add_argument("--fields-csv", default=DEFAULT_FIELDS_CSV, help="字段CSV文件路径")
    parser.add_argument("--page-name", default=PAGE_NAME, help="页面名称")
    args = parser.parse_args()

    api_base_url = args.base_url
    api_key = args.api_key
    templates_csv = args.templates_csv
    fields_csv = args.fields_csv
    page_name = args.page_name

    print("=" * 80)
    print("创建服务记录类型字段结构")
    print("=" * 80)
    print(f"API Base URL: {api_base_url}")
    print(f"页面名称: {page_name}")
    print(f"模板CSV: {templates_csv}")
    print(f"字段CSV: {fields_csv}")
    print("=" * 80)

    # 1. 读取模板数据
    print(f"\n[1/4] 读取模板数据...")
    try:
        templates = read_csv_data(templates_csv)
        print(f"      ✓ 读取到 {len(templates)} 个模板")
    except Exception as e:
        print(f"      ✗ 读取模板CSV失败: {e}")
        sys.exit(1)

    # 2. 读取字段定义数据
    print(f"\n[2/4] 读取字段定义...")
    try:
        fields_data = read_csv_data(fields_csv)
        # 构建字段名到字段信息的映射
        fields_map = {f["字段名"]: f for f in fields_data}
        print(f"      ✓ 读取到 {len(fields_data)} 个字段定义")
    except Exception as e:
        print(f"      ✗ 读取字段CSV失败: {e}")
        sys.exit(1)

    # 3. 创建"服务记录类型"字段
    print(f"\n[3/4] 创建服务记录类型字段...")
    
    # 构建选项
    service_type_options = build_service_record_type_options(templates)
    print(f"      选项数量: {len(service_type_options)}")
    for opt in service_type_options:
        print(f"        - {opt['label']} (ID: {opt['value']})")

    # 创建字段请求
    service_type_field = create_select_field(
        field_name="服务记录类型",
        field_label="服务记录类型",
        options_items=service_type_options,
        fill_instruction="请选择服务记录的类型"
    )

    request_data = {
        "page_name": page_name,
        "group_name": FIELD_GROUP_NAME,
        "fields": [service_type_field],
        "is_append": False
    }

    print(f"\n      发送请求创建字段...")
    try:
        response = send_upsert_request(api_base_url, api_key, request_data)
        if response.get("code") == 200 or response.get("success"):
            print(f"      ✓ 服务记录类型字段创建成功")
        else:
            print(f"      ✗ 创建失败: {response.get('message', '未知错误')}")
            sys.exit(1)
    except Exception as e:
        print(f"      ✗ 请求失败: {e}")
        sys.exit(1)

    # 4. 为每个模板创建字段组
    print(f"\n[4/4] 为每个模板创建字段组...")
    
    success_count = 0
    failed_count = 0

    for template in templates:
        template_id = template.get("id", "")
        template_name = template.get("name", "")
        template_content = template.get("template_content", "")
        
        if not template_id or not template_name:
            continue

        # 字段组名称
        group_name = f"服务记录-{template_name}"
        
        print(f"\n    处理: {template_name}")
        print(f"    字段组名称: {group_name}")

        # 提取模板中的变量
        variables = extract_variables(template_content)
        print(f"    模板变量数量: {len(variables)}")

        if not variables:
            print(f"    ⚠ 模板中没有变量，跳过")
            continue

        # 构建字段列表
        fields = []
        for var_name in sorted(variables):
            field_label = get_field_label(var_name, fields_data)
            fill_instruction = get_field_instruction(var_name, fields_data)
            
            field = create_text_field(
                field_name=var_name,
                field_label=field_label,
                fill_instruction=fill_instruction
            )
            fields.append(field)
            print(f"      - {var_name} ({field_label})")

        # 构建输出模板
        output_templates = {
            "default": {
                "template": template_content,
                "description": f"{template_name}服务记录输出模板"
            }
        }

        # 创建字段组请求
        request_data = {
            "page_name": page_name,
            "group_name": group_name,
            "fields": fields,
            "is_append": False,
            "output_templates": output_templates
        }

        print(f"    发送请求创建字段组...")
        try:
            response = send_upsert_request(api_base_url, api_key, request_data)
            if response.get("code") == 200 or response.get("success"):
                print(f"    ✓ 字段组创建成功")
                success_count += 1
            else:
                print(f"    ✗ 创建失败: {response.get('message', '未知错误')}")
                failed_count += 1
        except Exception as e:
            print(f"    ✗ 请求失败: {e}")
            failed_count += 1

    # 汇总结果
    print("\n" + "=" * 80)
    print("执行结果汇总")
    print("=" * 80)
    print(f"服务记录类型字段: 1 个 (✓ 成功)")
    print(f"模板字段组: {success_count} 个成功, {failed_count} 个失败")
    print(f"总计: {success_count + 1} 个")
    print("=" * 80)

    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
