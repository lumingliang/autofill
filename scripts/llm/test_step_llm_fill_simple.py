#!/usr/bin/env python3
"""
分步LLM填单测试脚本 - 简化版
只测试事件类型字段组
"""

import json
import sys
import uuid
from datetime import datetime

import requests

# 默认配置
DEFAULT_API_BASE_URL = "http://localhost:9999"
DEFAULT_API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"

# 测试用例：道路救援场景
TEST_CONVERSATION_RESCUE = """
【第1轮】
客服：您好，比亚迪汽车客服中心，请问有什么可以帮您？
用户：你好，我的车突然启动不了了，刚才还好好的。

【第2轮】
客服：您好，请问您的车辆型号是什么？车架号方便提供吗？
用户：我是比亚迪汉EV，车架号是LGXC14EAXN1234567。

【第3轮】
客服：好的，请问您现在车辆的具体位置在哪里？
用户：我在家里地下车库。

【第4轮】
客服：请问仪表盘上有显示什么故障灯吗？
用户：仪表盘上有个红色的电池图标在闪。

【第5轮】
客服：请问您现在车辆还能移动吗？
用户：完全动不了，需要拖车服务。

【第6轮】
客服：好的，请问您方便接收拖车的手机号码是多少？
用户：我的手机号是13812345678。
"""


def send_step_llm_fill_request(
    api_base_url: str,
    api_key: str,
    session_id: str,
    group_names: list,
    field_names: list,
    system_prompt_group: str,
    query: str,
    is_last: bool = False,
):
    """发送分步LLM填单请求"""
    import time

    url = f"{api_base_url}/api/autofill/llm/fill/step"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "session_id": session_id,
        "group_names": group_names,
        "field_names": field_names,
        "system_prompt_group": system_prompt_group,
        "query": query,
        "is_last": is_last
    }

    start_time = time.time()
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    elapsed_time = time.time() - start_time
    response.raise_for_status()

    result = response.json()
    if result.get("code") == 200 or result.get("success"):
        if "data" in result:
            result["data"]["client_elapsed_time"] = elapsed_time
    return result


def get_step_result(api_base_url: str, api_key: str, session_id: str):
    """获取分步填单完整结果"""
    url = f"{api_base_url}/api/autofill/llm/fill/step/result"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {"session_id": session_id}

    response = requests.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    return response.json()


def extract_field_value(field_data):
    """从字段数据中提取值"""
    if isinstance(field_data, dict):
        value = field_data.get("value", "")
        if isinstance(value, dict):
            return value.get("value", "")
        return value
    return field_data


def run_test():
    """运行简化版分步填单测试"""
    api_base_url = DEFAULT_API_BASE_URL
    api_key = DEFAULT_API_KEY
    session_id = f"test_{uuid.uuid4().hex[:12]}"
    conversation = TEST_CONVERSATION_RESCUE

    print("=" * 80)
    print("分步LLM填单测试 - 简化版（仅事件类型字段组）")
    print("=" * 80)
    print(f"Session ID: {session_id}")
    print(f"API Base URL: {api_base_url}")
    print("=" * 80)

    # ========== 步骤1：获取一级事件类型 ==========
    print("\n" + "-" * 80)
    print("【步骤1】获取一级事件类型")
    print("-" * 80)

    try:
        response1 = send_step_llm_fill_request(
            api_base_url=api_base_url,
            api_key=api_key,
            session_id=session_id,
            group_names=["事件类型"],
            field_names=["一级事件类型"],
            system_prompt_group="事件类型",
            query=conversation,
            is_last=False,
        )

        print(f"\n响应: {json.dumps(response1, ensure_ascii=False, indent=2)}")

        if response1.get("code") == 200 or response1.get("success"):
            data1 = response1.get("data", {})
            step1 = data1.get("step", 1)
            result1 = data1.get("result", {})
            elapsed_time = data1.get("elapsed_time", 0)
            client_elapsed_time = data1.get("client_elapsed_time", 0)

            print(f"\n✓ 步骤1成功 (第{step1}步)")
            print(f"  服务端用时: {elapsed_time:.2f}s | 客户端用时: {client_elapsed_time:.2f}s")

            field_data = result1.get("一级事件类型", {})
            value = extract_field_value(field_data)
            label = field_data.get("value", {}).get("label", value) if isinstance(field_data.get("value"), dict) else value
            print(f"  - 一级事件类型: {label} ({value})")

            event_type = label
        else:
            print(f"✗ 步骤1失败: {response1.get('message', '未知错误')}")
            return False

    except Exception as e:
        print(f"✗ 步骤1异常: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ========== 步骤2：获取二三级事件类型 ==========
    print("\n" + "-" * 80)
    print("【步骤2】获取二三级事件类型")
    print("-" * 80)
    print(f"一级事件类型: {event_type}")

    # 构建步骤2的字段名
    secondary_field_name = f"{event_type}-二三级事件类型"
    print(f"请求次字段: {secondary_field_name}")

    try:
        response2 = send_step_llm_fill_request(
            api_base_url=api_base_url,
            api_key=api_key,
            session_id=session_id,
            group_names=["事件类型"],
            field_names=[secondary_field_name],
            system_prompt_group="事件类型",
            query=conversation,
            is_last=True,  # 标记为最后一步
        )

        print(f"\n响应: {json.dumps(response2, ensure_ascii=False, indent=2)}")

        if response2.get("code") == 200 or response2.get("success"):
            data2 = response2.get("data", {})
            step2 = data2.get("step", 2)
            result2 = data2.get("result", {})
            merged_fields = data2.get("merged_fields", {})
            elapsed_time2 = data2.get("elapsed_time", 0)
            client_elapsed_time2 = data2.get("client_elapsed_time", 0)

            print(f"\n✓ 步骤2成功 (第{step2}步)")
            print(f"  服务端用时: {elapsed_time2:.2f}s | 客户端用时: {client_elapsed_time2:.2f}s")
            print(f"\n提取到的字段:")

            for field_name, field_data in result2.items():
                value = extract_field_value(field_data)
                label = field_data.get("value", {}).get("label", value) if isinstance(field_data.get("value"), dict) else value
                print(f"  - {field_name}: {label} ({value})")

            if merged_fields:
                print(f"\n【合并后的所有字段】({len(merged_fields)}个)")
                for field_name, value in merged_fields.items():
                    print(f"  - {field_name}: {value}")
        else:
            print(f"✗ 步骤2失败: {response2.get('message', '未知错误')}")
            return False

    except Exception as e:
        print(f"✗ 步骤2异常: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ========== 获取完整结果 ==========
    print("\n" + "-" * 80)
    print("【获取完整结果】")
    print("-" * 80)

    try:
        final_response = get_step_result(api_base_url, api_key, session_id)
        print(f"\n响应: {json.dumps(final_response, ensure_ascii=False, indent=2)}")

        if final_response.get("code") == 200 or final_response.get("success"):
            final_data = final_response.get("data", {})
            print(f"✓ 获取完整结果成功")
            print(f"  - 总步骤数: {final_data.get('total_steps', 0)}")
            print(f"  - 状态: {final_data.get('status', 'unknown')}")
    except Exception as e:
        print(f"✗ 获取完整结果异常: {e}")

    print("\n" + "=" * 80)
    print("测试完成!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
