#!/usr/bin/env python3
"""
通过API检查字段组详情
"""
import json
import requests

BASE_URL = "http://localhost:9999/api"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"


def check_field_group_schema():
    """检查字段组schema"""
    url = f"{BASE_URL}/autofill/field_groups/schema"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    print("=" * 70)
    print("检查字段组 schema (所有字段组)")
    print("=" * 70)
    
    try:
        resp = requests.post(url, headers=headers, json={"page_name": "用户信息页"}, timeout=30)
        result = resp.json()
        
        if result.get("code") == 200:
            data = result.get("data", {})
            fields = data.get("fields", [])
            print(f"\n找到 {len(fields)} 个字段:")
            for field in fields:
                print(f"  - {field['field_name']} ({field['field_label']})")
        else:
            print(f"错误: {result.get('msg')}")
    except Exception as e:
        print(f"异常: {e}")


def check_specific_group(group_name):
    """检查特定字段组"""
    url = f"{BASE_URL}/autofill/field_groups/schema"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    print(f"\n{'=' * 70}")
    print(f"检查字段组: {group_name}")
    print("=" * 70)
    
    try:
        resp = requests.post(url, headers=headers, json={
            "page_name": "用户信息页",
            "group_names": [group_name]
        }, timeout=30)
        result = resp.json()
        
        if result.get("code") == 200:
            data = result.get("data", {})
            fields = data.get("fields", [])
            print(f"\n找到 {len(fields)} 个字段:")
            for field in fields:
                print(f"  - {field['field_name']} ({field['field_label']})")
        else:
            print(f"错误: {result.get('msg')}")
    except Exception as e:
        print(f"异常: {e}")


def check_all_groups():
    """检查所有字段组"""
    url = f"{BASE_URL}/autofill/field_group"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    print("\n" + "=" * 70)
    print("列出所有字段组")
    print("=" * 70)
    
    try:
        resp = requests.post(url, headers=headers, json={"page_name": "用户信息页"}, timeout=30)
        result = resp.json()
        
        if result.get("code") == 200:
            groups = result.get("data", [])
            print(f"\n找到 {len(groups)} 个字段组:")
            for group in groups:
                print(f"\n  字段组: {group['group_name']}")
                print(f"    ID: {group['id']}")
                print(f"    字段数量: {len(group.get('field_specs', []))}")
                for field in group.get('field_specs', []):
                    print(f"      - {field['field_name']}")
        else:
            print(f"错误: {result.get('msg')}")
    except Exception as e:
        print(f"异常: {e}")


if __name__ == "__main__":
    check_field_group_schema()
    check_all_groups()
    
    # 检查可能的字段组
    possible_groups = ["default", "服务记录-拖车服务", "服务记录-道路救援请求", "道路救援请求"]
    for group_name in possible_groups:
        check_specific_group(group_name)
