#!/usr/bin/env python3
"""
分步LLM填单测试脚本 - 多行填写说明测试版
测试多行填写说明的字段，使用 jsonparser 方法
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
    method: str = "json_parser",  # 使用 json_parser 方法
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
        "is_last": is_last,
        "method": method  # 指定方法
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


def extract_field_label(field_data):
    """从字段数据中提取标签"""
    if isinstance(field_data, dict):
        value = field_data.get("value", {})
        if isinstance(value, dict):
            return value.get("label", "")
        return value
    return field_data


def run_test():
    """运行多行填写说明测试"""
    api_base_url = DEFAULT_API_BASE_URL
    api_key = DEFAULT_API_KEY
    session_id = f"test_{uuid.uuid4().hex[:12]}"
    conversation = TEST_CONVERSATION_RESCUE

    print("=" * 80)
    print("分步LLM填单测试 - 多行填写说明测试版")
    print("=" * 80)
    print(f"Session ID: {session_id}")
    print(f"API Base URL: {api_base_url}")
    print(f"Method: json_parser")
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
            method="json_parser",
        )

        print(f"\n响应: {json.dumps(response1, ensure_ascii=False, indent=2)}")

        if response1.get("code") == 200 or response1.get("success"):
            data1 = response1.get("data", {})
            step1 = data1.get("step", 1)
            fields1 = data1.get("fields", {})
            elapsed_time = data1.get("elapsed_time", 0)
            client_elapsed_time = data1.get("client_elapsed_time", 0)

            print(f"\n✓ 步骤1成功 (第{step1}步)")
            print(f"  服务端用时: {elapsed_time:.2f}s | 客户端用时: {client_elapsed_time:.2f}s")

            field_data = fields1.get("一级事件类型", {})
            value = extract_field_value(field_data)
            label = extract_field_label(field_data)
            print(f"  - 一级事件类型: {label} ({value})")

            event_type = label if label else "道路救援"
        else:
            print(f"✗ 步骤1失败: {response1.get('message', '未知错误')}")
            return False

    except Exception as e:
        print(f"✗ 步骤1异常: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ========== 步骤2：获取二三级事件类型（多行字段）==========
    print("\n" + "-" * 80)
    print("【步骤2】获取二三级事件类型（测试多行填写说明）")
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
            is_last=False,  # 不是最后一步
            method="json_parser",
        )

        print(f"\n响应: {json.dumps(response2, ensure_ascii=False, indent=2)}")

        if response2.get("code") == 200 or response2.get("success"):
            data2 = response2.get("data", {})
            step2 = data2.get("step", 2)
            fields2 = data2.get("fields", {})
            elapsed_time2 = data2.get("elapsed_time", 0)
            client_elapsed_time2 = data2.get("client_elapsed_time", 0)

            print(f"\n✓ 步骤2成功 (第{step2}步)")
            print(f"  服务端用时: {elapsed_time2:.2f}s | 客户端用时: {client_elapsed_time2:.2f}s")
            print(f"\n提取到的字段:")

            for field_name, field_data in fields2.items():
                value = extract_field_value(field_data)
                label = extract_field_label(field_data)
                print(f"  - {field_name}: {label} ({value})")
        else:
            print(f"✗ 步骤2失败: {response2.get('message', '未知错误')}")
            return False

    except Exception as e:
        print(f"✗ 步骤2异常: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ========== 步骤3：测试多行字段（test_multiline_field）==========
    print("\n" + "-" * 80)
    print("【步骤3】测试多行填写说明字段")
    print("-" * 80)
    print("测试字段: test_multiline_field (测试多行字段)")

    try:
        response3 = send_step_llm_fill_request(
            api_base_url=api_base_url,
            api_key=api_key,
            session_id=session_id,
            group_names=["default"],  # 使用 default 字段组
            field_names=["test_multiline_field"],
            system_prompt_group=None,
            query=conversation,
            is_last=True,  # 标记为最后一步
            method="json_parser",
        )

        print(f"\n响应: {json.dumps(response3, ensure_ascii=False, indent=2)}")

        if response3.get("code") == 200 or response3.get("success"):
            data3 = response3.get("data", {})
            step3 = data3.get("step", 3)
            fields3 = data3.get("fields", {})
            elapsed_time3 = data3.get("elapsed_time", 0)
            client_elapsed_time3 = data3.get("client_elapsed_time", 0)

            print(f"\n✓ 步骤3成功 (第{step3}步)")
            print(f"  服务端用时: {elapsed_time3:.2f}s | 客户端用时: {client_elapsed_time3:.2f}s")
            print(f"\n提取到的字段:")

            for field_name, field_data in fields3.items():
                value = extract_field_value(field_data)
                label = extract_field_label(field_data)
                print(f"  - {field_name}: {label} ({value})")

            if fields3:
                print(f"\n【本步骤字段】({len(fields3)}个)")
                for field_name, value in fields3.items():
                    print(f"  - {field_name}: {value}")
        else:
            print(f"✗ 步骤3失败: {response3.get('message', '未知错误')}")
            return False

    except Exception as e:
        print(f"✗ 步骤3异常: {e}")
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
            
            fields = final_data.get("fields", {})
            if fields:
                print(f"\n【所有字段汇总】({len(fields)}个)")
                for field_name, value in fields.items():
                    print(f"  - {field_name}: {value}")
    except Exception as e:
        print(f"✗ 获取完整结果异常: {e}")

    print("\n" + "=" * 80)
    print("测试完成!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
