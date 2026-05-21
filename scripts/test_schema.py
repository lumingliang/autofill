#!/usr/bin/env python3
"""
测试字段组schema构建
"""

import json
import requests

# 默认配置
DEFAULT_API_BASE_URL = "http://localhost:9999"
DEFAULT_API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"


def test_field_group_schema():
    """测试字段组schema接口"""
    url = f"{DEFAULT_API_BASE_URL}/api/autofill/field_group/schema"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEFAULT_API_KEY}"
    }

    payload = {
        "group_names": ["事件类型"],
        "field_names": ["一级事件类型"]
    }

    print("=" * 80)
    print("测试字段组Schema接口")
    print("=" * 80)
    print(f"请求: {json.dumps(payload, ensure_ascii=False)}")

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()

        print(f"\n响应:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        if result.get("code") == 200 or result.get("success"):
            data = result.get("data", {})
            schema = data.get("unified_function_schema")
            if schema:
                print("\n" + "=" * 80)
                print("FC Schema 详情:")
                print("=" * 80)
                print(json.dumps(schema, ensure_ascii=False, indent=2))
        else:
            print(f"\n✗ 失败: {result.get('message', '未知错误')}")

    except Exception as e:
        print(f"\n✗ 异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_field_group_schema()
