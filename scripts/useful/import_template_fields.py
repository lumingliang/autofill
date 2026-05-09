#!/usr/bin/env python3
"""
从CSV文件导入模板字段作为文本类型字段

使用方法:
    python import_template_fields.py [--api-key API_KEY] [--base-url BASE_URL] [--csv-path CSV_PATH]

示例:
    python import_template_fields.py
    python import_template_fields.py --api-key af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR
    python import_template_fields.py --base-url http://localhost:9999 --csv-path /path/to/fields.csv
"""

import argparse
import csv
import json
import sys
from typing import Dict, List, Any

import requests

# 默认配置
DEFAULT_API_BASE_URL = "http://localhost:9999"
DEFAULT_API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
DEFAULT_CSV_PATH = "/Users/lu/code/code/py/autofill/test_csv_data/template_fields.csv"
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


def create_field_group_request(page_name: str, group_name: str, fields: List[Dict]) -> Dict:
    """创建字段组请求体"""
    return {
        "page_name": page_name,
        "group_name": group_name,
        "fields": fields,
        "is_append": False
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


def batch_create_fields(
    api_base_url: str,
    api_key: str,
    page_name: str,
    group_name: str,
    fields_data: List[Dict[str, str]],
    batch_size: int = 20
) -> tuple:
    """
    批量创建字段
    返回: (成功数量, 失败数量)
    """
    total = len(fields_data)
    success_count = 0
    failed_count = 0
    
    # 分批处理
    for i in range(0, total, batch_size):
        batch = fields_data[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size
        
        print(f"\n  处理第 {batch_num}/{total_batches} 批，共 {len(batch)} 个字段...")
        
        # 构建字段列表
        fields = []
        for field_data in batch:
            field_name = field_data.get("字段名", "").strip()
            field_label = field_data.get("字段标签", "").strip()
            fill_instruction = field_data.get("填写说明", "").strip()
            
            if not field_name or not field_label:
                print(f"    ⚠ 跳过无效数据: {field_data}")
                continue
            
            field = create_text_field(
                field_name=field_name,
                field_label=field_label,
                fill_instruction=fill_instruction
            )
            fields.append(field)
            print(f"    - {field_name} ({field_label})")
        
        if not fields:
            continue
        
        # 发送请求
        request_data = create_field_group_request(
            page_name=page_name,
            group_name=group_name,
            fields=fields
        )
        
        try:
            response = send_upsert_request(api_base_url, api_key, request_data)
            if response.get("code") == 200 or response.get("success"):
                print(f"    ✓ 本批创建成功: {len(fields)} 个字段")
                success_count += len(fields)
            else:
                print(f"    ✗ 本批创建失败: {response.get('message', '未知错误')}")
                failed_count += len(fields)
        except Exception as e:
            print(f"    ✗ 请求失败: {e}")
            failed_count += len(fields)
    
    return success_count, failed_count


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="从CSV导入模板字段")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API Key (默认使用预设值)")
    parser.add_argument("--base-url", default=DEFAULT_API_BASE_URL, help="API基础URL")
    parser.add_argument("--csv-path", default=DEFAULT_CSV_PATH, help="字段CSV文件路径")
    parser.add_argument("--page-name", default=PAGE_NAME, help="页面名称")
    parser.add_argument("--group-name", default=FIELD_GROUP_NAME, help="字段组名称")
    parser.add_argument("--batch-size", type=int, default=20, help="每批创建的字段数量")
    args = parser.parse_args()

    csv_path = args.csv_path
    api_base_url = args.base_url
    api_key = args.api_key
    page_name = args.page_name
    group_name = args.group_name
    batch_size = args.batch_size

    print("=" * 80)
    print("导入模板字段")
    print("=" * 80)
    print(f"API Base URL: {api_base_url}")
    print(f"页面名称: {page_name}")
    print(f"字段组名称: {group_name}")
    print(f"CSV文件: {csv_path}")
    print(f"批次大小: {batch_size}")
    print("=" * 80)

    # 1. 读取CSV数据
    print(f"\n[1/3] 读取CSV文件...")
    try:
        data = read_csv_data(csv_path)
        print(f"      ✓ 读取到 {len(data)} 个字段定义")
    except Exception as e:
        print(f"      ✗ 读取CSV失败: {e}")
        sys.exit(1)

    if not data:
        print("没有数据可导入")
        sys.exit(0)

    # 2. 批量创建字段
    print(f"\n[2/3] 批量创建字段...")
    success_count, failed_count = batch_create_fields(
        api_base_url=api_base_url,
        api_key=api_key,
        page_name=page_name,
        group_name=group_name,
        fields_data=data,
        batch_size=batch_size
    )

    # 3. 验证部分字段
    print(f"\n[3/3] 验证字段创建...")
    verification_count = min(3, len(data))
    verified = 0
    for i in range(verification_count):
        field_name = data[i].get("字段名", "").strip()
        if field_name:
            if test_field_creation(api_base_url, api_key, page_name, field_name):
                print(f"      ✓ {field_name} 验证通过")
                verified += 1
            else:
                print(f"      ✗ {field_name} 验证失败")

    # 汇总结果
    print("\n" + "=" * 80)
    print("执行结果汇总")
    print("=" * 80)
    print(f"总字段数: {len(data)}")
    print(f"创建成功: {success_count}")
    print(f"创建失败: {failed_count}")
    print(f"验证通过: {verified}/{verification_count}")
    print("=" * 80)

    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
