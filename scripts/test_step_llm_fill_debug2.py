#!/usr/bin/env python3
"""
分步LLM填单测试脚本 - 调试版2
测试字段配置是否正确加载，添加更多调试信息
"""

import json
import requests

# 默认配置
DEFAULT_API_BASE_URL = "http://localhost:9999"
DEFAULT_API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"

# 更明确的测试对话，包含明确的事件类型
TEST_CONVERSATION = """
用户：我的车在路上抛锚了，需要道路救援。
客服：请问您的车辆型号是什么？
用户：比亚迪汉EV。
"""


def test_step_llm_fill():
    """测试分步填单接口"""
    import uuid
    import time

    url = f"{DEFAULT_API_BASE_URL}/api/autofill/llm/fill/step"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEFAULT_API_KEY}"
    }

    session_id = f"debug2_{uuid.uuid4().hex[:8]}"

    payload = {
        "session_id": session_id,
        "group_names": ["事件类型"],
        "field_names": ["一级事件类型"],
        "system_prompt_group": "事件类型",
        "query": TEST_CONVERSATION,
        "is_last": True,
        "method": "pydantic_parser"  # 显式指定使用 pydantic_parser 方法
    }

    print("=" * 80)
    print("测试分步LLM填单接口 - 调试版2")
    print("=" * 80)
    print(f"Session ID: {session_id}")
    print(f"请求: {json.dumps(payload, ensure_ascii=False, indent=2)}")

    try:
        start_time = time.time()
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        elapsed_time = time.time() - start_time
        response.raise_for_status()
        result = response.json()

        print(f"\n响应 (用时: {elapsed_time:.2f}s):")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        if result.get("code") == 200 or result.get("success"):
            data = result.get("data", {})
            step_result = data.get("result", {})
            print(f"\n✓ 填单请求成功")
            print(f"  - 步骤: {data.get('step')}")
            print(f"  - 状态: {data.get('status')}")
            print(f"  - 提取字段数: {len(step_result)}")

            if step_result:
                for field_name, field_data in step_result.items():
                    print(f"\n  字段: {field_name}")
                    print(f"    数据: {json.dumps(field_data, ensure_ascii=False)}")
            else:
                print("\n⚠ 警告: 没有提取到任何字段值")
                print("  可能原因:")
                print("  1. LLM没有正确理解字段的选项值")
                print("  2. 系统提示词不够明确")
                print("  3. 对话内容中没有明确提到选项中的值")
        else:
            print(f"\n✗ 失败: {result.get('message', '未知错误')}")

    except Exception as e:
        print(f"\n✗ 异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_step_llm_fill()
