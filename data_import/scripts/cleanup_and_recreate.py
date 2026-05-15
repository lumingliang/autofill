#!/usr/bin/env python3
"""
清理并重新创建所有字段和字段组
1. 删除现有字段组和字段（直接删除3个关联表）
2. 创建事件类型字段（级联字段）
3. 创建400电话字段
4. 创建服务记录类型字段和字段组
"""

import argparse
import csv
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Optional

import requests
import yaml

# 默认配置
DEFAULT_API_BASE_URL = "http://localhost:9999"
DEFAULT_API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
PAGE_NAME = "话务工作台"


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


def list_field_groups(api_base_url: str, api_key: str, page_name: str) -> List[Dict]:
    """获取页面下的所有字段组"""
    try:
        result = send_request(
            api_base_url, api_key,
            "/api/autofill/field_spec/list",
            {"page_name": page_name}
        )
        return result.get("data", [])
    except Exception as e:
        print(f"获取字段组列表失败: {e}")
        return []


def delete_field_group(api_base_url: str, api_key: str, group_name: str, page_name: str) -> bool:
    """删除字段组"""
    try:
        # 通过创建空字段组的方式清空字段
        send_request(
            api_base_url, api_key,
            "/api/autofill/field_group/upsert",
            {
                "page_name": page_name,
                "group_name": group_name,
                "fields": [],
                "is_append": False
            }
        )
        print(f"  ✓ 清空字段组: {group_name}")
        return True
    except Exception as e:
        print(f"  ✗ 清空字段组失败 {group_name}: {e}")
        return False


def clear_all_field_specs_and_groups(api_base_url: str, api_key: str, page_name: str) -> bool:
    """清空所有字段定义和字段组（通过字段组upsert接口清空）"""
    print("\n" + "="*60)
    print("清空所有字段和字段组")
    print("="*60)

    # 获取页面下的所有字段组
    try:
        result = send_request(
            api_base_url, api_key,
            "/api/autofill/field_spec/list",
            {"page_name": page_name}
        )
        field_specs = result.get("data", [])
        print(f"  发现 {len(field_specs)} 个字段定义")

        # 清空每个字段组
        for spec in field_specs:
            field_groups = spec.get("field_groups", [])
            for group in field_groups:
                group_name = group.get("group_name", "")
                if group_name:
                    # 通过创建空字段组来清空
                    try:
                        send_request(
                            api_base_url, api_key,
                            "/api/autofill/field_group/upsert",
                            {
                                "page_name": page_name,
                                "group_name": group_name,
                                "fields": [],
                                "is_append": False
                            }
                        )
                        print(f"    ✓ 清空字段组: {group_name}")
                    except Exception as e:
                        print(f"    ⚠ 清空字段组失败 {group_name}: {e}")

        print(f"  ✓ 已清空所有字段组")
        return True
    except Exception as e:
        print(f"  ⚠ 获取字段列表失败: {e}")
        return False


def create_select_field(field_name: str, field_label: str, options_items: List[Dict], 
                        fill_instruction: str = "") -> Dict:
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


def create_text_field(field_name: str, field_label: str, fill_instruction: str = "") -> Dict:
    """创建文本输入字段"""
    return {
        "field_name": field_name,
        "field_label": field_label,
        "field_type": "text",
        "fill_instruction": fill_instruction
    }


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
    return list(set(variables))


def create_event_type_fields(api_base_url: str, api_key: str, page_name: str, csv_path: str):
    """创建事件类型级联字段（基于event_types.csv）
    创建一级事件类型主字段，以及每个一级事件类型对应的二三级事件类型次字段
    """
    print("\n" + "="*60)
    print("创建事件类型字段（级联字段）")
    print("="*60)

    # 读取CSV数据
    data = read_csv_data(csv_path)
    print(f"读取到 {len(data)} 行数据")

    # 构建层级结构
    hierarchy = defaultdict(lambda: {"id": "", "instruction": "", "children": defaultdict(lambda: {"id": "", "instruction": "", "children": {}})})

    for row in data:
        level1_name = row.get("一级事件类型", "").strip()
        level1_id = row.get("一级事件类型ID", "").strip()
        level1_inst = row.get("一级事件类型填写说明", "").strip()

        level2_name = row.get("二级事件类型", "").strip()
        level2_id = row.get("二级事件类型ID", "").strip()
        level2_inst = row.get("二级事件类型填写说明", "").strip()

        level3_name = row.get("三级事件类型", "").strip()
        level3_id = row.get("三级事件类型ID", "").strip()
        level3_inst = row.get("三级事件类型填写说明", "").strip()

        if not level1_name:
            continue

        # 设置一级数据
        hierarchy[level1_name]["id"] = level1_id
        hierarchy[level1_name]["instruction"] = level1_inst

        if level2_name:
            hierarchy[level1_name]["children"][level2_name]["id"] = level2_id
            hierarchy[level1_name]["children"][level2_name]["instruction"] = level2_inst

            if level3_name:
                hierarchy[level1_name]["children"][level2_name]["children"][level3_name] = {
                    "id": level3_id,
                    "instruction": level3_inst
                }

    print(f"组织了 {len(hierarchy)} 个一级分类")

    # 构建主字段选项（一级事件类型）
    main_options = []
    for name, data in hierarchy.items():
        main_options.append({
            "label": name,
            "value": data["id"],
            "fill_instruction": data["instruction"]
        })

    # 创建主字段
    main_field = create_select_field(
        field_name="一级事件类型",
        field_label="一级事件类型",
        options_items=main_options,
        fill_instruction="请选择一级事件类型"
    )

    # 创建次字段（每个一级事件类型一个次字段）
    secondary_fields = []

    for level1_name, level1_data in hierarchy.items():
        secondary_options = []

        for level2_name, level2_data in level1_data["children"].items():
            for level3_name, level3_data in level2_data["children"].items():
                # 组合二级和三级名称
                combined_name = f"{level2_name}-{level3_name}"
                combined_id = f"{level2_data['id']}_{level3_data['id']}"
                # 合并填写说明
                combined_inst = f"{level2_data['instruction']}\n{level3_data['instruction']}".strip()

                secondary_options.append({
                    "label": combined_name,
                    "value": combined_id,
                    "fill_instruction": combined_inst
                })

        if secondary_options:
            field_name = f"{level1_name}-二三级事件类型"
            field_label = f"{level1_name}-二三级事件类型"

            secondary_field = create_select_field(
                field_name=field_name,
                field_label=field_label,
                options_items=secondary_options,
                fill_instruction=f"请选择{level1_name}的二三级事件类型"
            )
            secondary_fields.append(secondary_field)

    print(f"主字段选项数: {len(main_options)}")
    print(f"次字段数量: {len(secondary_fields)}")

    # 创建字段组 - 先创建主字段
    try:
        send_request(
            api_base_url, api_key,
            "/api/autofill/field_group/upsert",
            {
                "page_name": page_name,
                "group_name": "事件类型",
                "fields": [main_field],
                "is_append": False
            }
        )
        print(f"✓ 主字段创建成功: 一级事件类型 ({len(main_options)} 个选项)")
    except Exception as e:
        print(f"✗ 创建主字段失败: {e}")
        return False

    # 分批创建次字段
    if secondary_fields:
        batch_size = 5
        for i in range(0, len(secondary_fields), batch_size):
            batch = secondary_fields[i:i+batch_size]
            try:
                send_request(
                    api_base_url, api_key,
                    "/api/autofill/field_group/upsert",
                    {
                        "page_name": page_name,
                        "group_name": "事件类型",
                        "fields": batch,
                        "is_append": True
                    }
                )
                print(f"✓ 批次 {i//batch_size + 1}/{(len(secondary_fields)-1)//batch_size + 1}: {len(batch)} 个次字段创建成功")
                time.sleep(0.5)
            except Exception as e:
                print(f"✗ 批次 {i//batch_size + 1} 创建失败: {e}")
                return False

    print(f"✓ 事件类型字段组创建完成，共 {1 + len(secondary_fields)} 个字段")
    return True


def create_400_phone_field(api_base_url: str, api_key: str, page_name: str, csv_path: str):
    """创建400电话字段"""
    print("\n" + "="*60)
    print("创建400电话字段")
    print("="*60)

    # 读取CSV数据
    data = read_csv_data(csv_path)
    print(f"读取到 {len(data)} 行选项数据")

    # 构建选项
    options = []
    for row in data:
        option_label = row.get("选项标签", "").strip()
        option_value = row.get("选项值", "").strip()
        fill_instruction = row.get("填写说明", "").strip()

        if option_label and option_value:
            options.append({
                "label": option_label,
                "value": option_value,
                "fill_instruction": fill_instruction
            })

    print(f"选项数量: {len(options)}")

    # 创建字段
    field = create_select_field(
        field_name="test_400_phone",
        field_label="400电话事件类型",
        options_items=options,
        fill_instruction="请选择400电话事件类型"
    )

    try:
        send_request(
            api_base_url, api_key,
            "/api/autofill/field_group/upsert",
            {
                "page_name": page_name,
                "group_name": "400电话字段",
                "fields": [field],
                "is_append": False
            }
        )
        print("✓ 400电话字段创建成功")
        return True
    except Exception as e:
        print(f"✗ 创建400电话字段失败: {e}")
        return False


def create_service_record_structure(api_base_url: str, api_key: str, page_name: str,
                                    templates_csv: str, fields_csv: str):
    """创建服务记录类型字段结构"""
    print("\n" + "="*60)
    print("创建服务记录类型字段结构")
    print("="*60)
    
    # 读取模板数据
    templates = read_csv_data(templates_csv)
    print(f"读取到 {len(templates)} 个模板")
    
    # 读取字段定义数据
    fields_data = read_csv_data(fields_csv)
    fields_map = {f["字段名"]: f for f in fields_data}
    print(f"读取到 {len(fields_data)} 个字段定义")
    
    # 1. 创建"服务记录类型"字段
    print("\n[1/2] 创建服务记录类型字段...")
    service_type_options = []
    for template in templates:
        template_id = template.get("id", "").strip()
        template_name = template.get("name", "").strip()
        summary = template.get("summary", "").strip()
        
        if template_id and template_name:
            service_type_options.append({
                "label": template_name,
                "value": template_id,
                "fill_instruction": summary
            })
    
    service_type_field = create_select_field(
        field_name="服务记录类型",
        field_label="服务记录类型",
        options_items=service_type_options,
        fill_instruction="请选择服务记录的类型"
    )
    
    try:
        send_request(
            api_base_url, api_key,
            "/api/autofill/field_group/upsert",
            {
                "page_name": page_name,
                "group_name": "服务记录类型",
                "fields": [service_type_field],
                "is_append": False
            }
        )
        print(f"✓ 服务记录类型字段创建成功，共 {len(service_type_options)} 个选项")
    except Exception as e:
        print(f"✗ 创建服务记录类型字段失败: {e}")
        return False
    
    # 2. 为每个模板创建字段组
    print("\n[2/2] 为每个模板创建字段组...")
    success_count = 0
    failed_count = 0
    
    for template in templates:
        template_id = template.get("id", "").strip()
        template_name = template.get("name", "").strip()
        template_content = template.get("template_content", "").strip()
        
        if not template_id or not template_name:
            continue
        
        group_name = f"服务记录-{template_name}"
        
        # 提取模板中的变量
        variables = extract_variables(template_content)
        
        if not variables:
            print(f"  ⚠ {template_name}: 模板中没有变量，跳过")
            continue
        
        # 构建字段列表
        fields = []
        for var_name in sorted(variables):
            field_info = fields_map.get(var_name, {})
            field_label = field_info.get("字段标签", var_name)
            fill_instruction = field_info.get("填写说明", "")
            
            field = create_text_field(
                field_name=var_name,
                field_label=field_label,
                fill_instruction=fill_instruction
            )
            fields.append(field)
        
        # 构建输出模板
        output_templates = {
            "default": {
                "template": template_content,
                "description": f"{template_name}服务记录输出模板"
            }
        }
        
        # 创建字段组
        try:
            send_request(
                api_base_url, api_key,
                "/api/autofill/field_group/upsert",
                {
                    "page_name": page_name,
                    "group_name": group_name,
                    "fields": fields,
                    "is_append": False,
                    "output_templates": output_templates
                }
            )
            print(f"  ✓ {template_name}: {len(fields)} 个字段")
            success_count += 1
        except Exception as e:
            print(f"  ✗ {template_name}: {e}")
            failed_count += 1
    
    print(f"\n服务记录字段组: {success_count} 个成功, {failed_count} 个失败")
    return failed_count == 0


def main():
    parser = argparse.ArgumentParser(description="清理并重新创建所有字段和字段组")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API Key")
    parser.add_argument("--base-url", default=DEFAULT_API_BASE_URL, help="API基础URL")
    parser.add_argument("--page-name", default=PAGE_NAME, help="页面名称")
    parser.add_argument("--skip-cleanup", action="store_true", help="跳过清理步骤")
    args = parser.parse_args()
    
    api_base_url = args.base_url
    api_key = args.api_key
    page_name = args.page_name
    
    print("="*60)
    print("清理并重新创建所有字段和字段组")
    print("="*60)
    print(f"API Base URL: {api_base_url}")
    print(f"页面名称: {page_name}")
    
    # 文件路径 - 相对于脚本所在目录
    script_dir = Path(__file__).parent.parent
    data_dir = script_dir / "data"
    event_types_csv = data_dir / "event_types.csv"
    phone_field_csv = data_dir / "phone_field_options.csv"
    templates_csv = data_dir / "templates_export.csv"
    fields_csv = data_dir / "template_fields.csv"

    # 1. 清理现有数据（清空所有字段和字段组）
    if not args.skip_cleanup:
        print("\n" + "="*60)
        print("步骤 1: 清空所有字段和字段组")
        print("="*60)
        clear_all_field_specs_and_groups(api_base_url, api_key, page_name)
        print("清理完成")

    # 2. 创建事件类型字段（级联字段）
    print("\n步骤 2: 创建事件类型字段")
    success1 = create_event_type_fields(api_base_url, api_key, page_name, str(event_types_csv))

    # 3. 创建400电话字段
    print("\n步骤 3: 创建400电话字段")
    success2 = create_400_phone_field(api_base_url, api_key, page_name, str(phone_field_csv))

    # 4. 创建服务记录结构
    print("\n步骤 4: 创建服务记录类型字段结构")
    success3 = create_service_record_structure(api_base_url, api_key, page_name,
                                                str(templates_csv), str(fields_csv))

    # 汇总
    print("\n" + "="*60)
    print("执行结果汇总")
    print("="*60)
    print(f"事件类型字段: {'✓ 成功' if success1 else '✗ 失败'}")
    print(f"400电话字段: {'✓ 成功' if success2 else '✗ 失败'}")
    print(f"服务记录结构: {'✓ 成功' if success3 else '✗ 失败'}")
    print("="*60)

    if success1 and success2 and success3:
        print("所有字段和字段组创建成功！")
        return 0
    else:
        print("部分创建失败，请检查日志")
        return 1


if __name__ == "__main__":
    sys.exit(main())
