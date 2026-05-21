#!/usr/bin/env python3
"""
分步LLM填单测试脚本 - 调试版
测试字段配置是否正确加载
"""

import json
import requests

# 默认配置
DEFAULT_API_BASE_URL = "http://localhost:9999"
DEFAULT_API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"

# 简单的测试对话
TEST_CONVERSATION = """
客服：您好，请问有什么可以帮您？
用户：我的车需要道路救援，启动不了了。
"""


def test_field_group_schema():
    """测试字段组schema接口，检查字段配置是否正确"""
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

        print(f"\n响应: {json.dumps(result, ensure_ascii=False, indent=2)}")

        if result.get("code") == 200 or result.get("success"):
            data = result.get("data", {})
            field_groups = data.get("field_groups", [])
            print(f"\n✓ 成功获取字段组配置")
            print(f"  - 字段组数量: {len(field_groups)}")

            for fg in field_groups:
                print(f"\n  字段组: {fg.get('group_name')}")
                fields = fg.get("fields", [])
                print(f"    字段数量: {len(fields)}")
                for f in fields:
                    print(f"    - {f.get('field_name')} ({f.get('field_label')}) - {f.get('field_type')}")

            # 检查 unified_function_schema
            schema = data.get("unified_function_schema")
            if schema:
                print(f"\n✓ unified_function_schema 存在")
                print(f"  - 名称: {schema.get('name')}")
                params = schema.get("parameters", {})
                props = params.get("properties", {})
                print(f"  - 参数数量: {len(props)}")
                for prop_name in props.keys():
                    print(f"    - {prop_name}")
            else:
                print(f"\n✗ unified_function_schema 不存在")
        else:
            print(f"\n✗ 失败: {result.get('message', '未知错误')}")

    except Exception as e:
        print(f"\n✗ 异常: {e}")
        import traceback
        traceback.print_exc()


def test_step_llm_fill():
    """测试分步填单接口"""
    import uuid
    import time

    url = f"{DEFAULT_API_BASE_URL}/api/autofill/llm/fill/step"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEFAULT_API_KEY}"
    }

    session_id = f"debug_{uuid.uuid4().hex[:8]}"

    payload = {
        "session_id": session_id,
        "group_names": ["事件类型"],
        "field_names": ["一级事件类型"],
        "system_prompt_group": "事件类型",
        "query": TEST_CONVERSATION,
        "is_last": True  # 直接测试最后一步
    }

    print("\n" + "=" * 80)
    print("测试分步LLM填单接口")
    print("=" * 80)
    print(f"Session ID: {session_id}")
    print(f"请求: {json.dumps(payload, ensure_ascii=False)}")

    try:
        start_time = time.time()
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        elapsed_time = time.time() - start_time
        response.raise_for_status()
        result = response.json()

        print(f"\n响应 (用时: {elapsed_time:.2f}s): {json.dumps(result, ensure_ascii=False, indent=2)}")

        if result.get("code") == 200 or result.get("success"):
            data = result.get("data", {})
            step_result = data.get("result", {})
            print(f"\n✓ 填单成功")
            print(f"  - 步骤: {data.get('step')}")
            print(f"  - 状态: {data.get('status')}")
            print(f"  - 提取字段数: {len(step_result)}")

            for field_name, field_data in step_result.items():
                print(f"\n  字段: {field_name}")
                print(f"    数据: {json.dumps(field_data, ensure_ascii=False)}")
        else:
            print(f"\n✗ 失败: {result.get('message', '未知错误')}")

    except Exception as e:
        print(f"\n✗ 异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_field_group_schema()
    test_step_llm_fill()
