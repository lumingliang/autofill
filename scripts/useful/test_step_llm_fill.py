#!/usr/bin/env python3
"""
分步LLM填单测试脚本 - 简化版
测试场景：基于session的分步填单流程

使用方法:
    python test_step_llm_fill.py [选项]

示例:
    # 使用默认测试用例（道路救援场景）
    python test_step_llm_fill.py

    # 指定session_id
    python test_step_llm_fill.py --session-id my_session_001

    # 使用特定方法
    python test_step_llm_fill.py --method with_structured_output

    # 保存结果
    python test_step_llm_fill.py --output result.json
"""

import argparse
import json
import sys
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

import requests

# 默认配置
DEFAULT_API_BASE_URL = "http://localhost:9999"
DEFAULT_API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
PAGE_NAME = "用户信息页"

# 测试用例：道路救援场景
TEST_CONVERSATION = """
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
    page_name: str,
    group_fields: Dict[str, List[str]],
    query: str,
    method: str = None,
    is_last: bool = False,
    memory_rounds: int = 0
) -> Dict:
    """发送分步LLM填单请求"""
    import time

    url = f"{api_base_url}/api/autofill/llm/fill/step"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "session_id": session_id,
        "page_name": page_name,
        "group_fields": group_fields,
        "query": query,
        "is_last": is_last
    }

    if method:
        payload["method"] = method

    if memory_rounds > 0:
        payload["memory_rounds"] = memory_rounds

    start_time = time.time()
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    elapsed_time = time.time() - start_time
    response.raise_for_status()

    result = response.json()
    # 添加客户端用时信息
    if result.get("code") == 200 or result.get("success"):
        if "data" in result:
            result["data"]["client_elapsed_time"] = elapsed_time
    return result


def get_step_result(
    api_base_url: str,
    api_key: str,
    session_id: str
) -> Dict:
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


def extract_field_value(field_data: Any) -> Any:
    """从字段数据中提取值"""
    if isinstance(field_data, dict):
        value = field_data.get("value", "")
        if isinstance(value, dict):
            return value.get("value", "")
        return value
    return field_data


def run_step_test(
    api_base_url: str,
    api_key: str,
    page_name: str,
    session_id: str,
    conversation: str,
    method: str = None,
    memory_rounds: int = 0
) -> Dict:
    """运行分步测试"""

    print("=" * 80)
    print("分步LLM填单测试")
    print("=" * 80)
    print(f"Session ID: {session_id}")
    print(f"API Base URL: {api_base_url}")
    print(f"页面名称: {page_name}")
    if method:
        print(f"使用方法: {method}")
    print("=" * 80)

    results = {
        "session_id": session_id,
        "steps": [],
        "timestamp": datetime.now().isoformat()
    }

    # ========== 步骤1：获取一级事件类型和服务记录类型 ==========
    print("\n" + "=" * 80)
    print("【步骤1】获取一级事件类型和服务记录类型")
    print("=" * 80)

    step1_fields = {"default": ["一级事件类型", "服务记录类型"]}

    try:
        response1 = send_step_llm_fill_request(
            api_base_url=api_base_url,
            api_key=api_key,
            session_id=session_id,
            page_name=page_name,
            group_fields=step1_fields,
            query=conversation,
            method=method,
            is_last=False,
            memory_rounds=memory_rounds
        )

        if response1.get("code") == 200 or response1.get("success"):
            data1 = response1.get("data", {})
            step1 = data1.get("step", 1)
            result1 = data1.get("result", {})
            elapsed_time = data1.get("elapsed_time", 0)
            client_elapsed_time = data1.get("client_elapsed_time", 0)

            print(f"\n✓ 步骤1成功 (第{step1}步)")
            print(f"  服务端用时: {elapsed_time:.2f}s | 客户端用时: {client_elapsed_time:.2f}s")

            step1_extracted = {}
            for field_name in ["一级事件类型", "服务记录类型"]:
                field_data = result1.get(field_name, {})
                value = extract_field_value(field_data)
                label = field_data.get("value", {}).get("label", value) if isinstance(field_data.get("value"), dict) else value
                step1_extracted[field_name] = {"value": value, "label": label}
                print(f"  - {field_name}: {label} ({value})")

            results["steps"].append({
                "step": 1,
                "fields": step1_extracted,
                "status": "success",
                "elapsed_time": elapsed_time,
                "client_elapsed_time": client_elapsed_time
            })
        else:
            print(f"✗ 步骤1失败: {response1.get('message', '未知错误')}")
            results["steps"].append({"step": 1, "status": "failed", "error": response1.get('message')})
            return results

    except Exception as e:
        print(f"✗ 步骤1异常: {e}")
        results["steps"].append({"step": 1, "status": "error", "error": str(e)})
        return results

    # ========== 步骤2：获取详细字段信息（最后一步） ==========
    print("\n" + "=" * 80)
    print("【步骤2】获取详细字段信息（最后一步）")
    print("=" * 80)

    # 根据步骤1的结果构建字段组请求
    service_type = step1_extracted.get("服务记录类型", {}).get("label", "")
    event_type = step1_extracted.get("一级事件类型", {}).get("label", "")

    print(f"服务记录类型: {service_type}")
    print(f"一级事件类型: {event_type}")

    step2_fields = {}
    if service_type:
        step2_fields[f"服务记录-{service_type}"] = []
    if event_type:
        step2_fields["default"] = [f"{event_type}_二三级事件类型"]

    if not step2_fields:
        print("✗ 无法确定要请求的字段组")
        results["steps"].append({"step": 2, "status": "failed", "error": "无法确定字段组"})
        return results

    print(f"请求字段组: {list(step2_fields.keys())}")

    try:
        response2 = send_step_llm_fill_request(
            api_base_url=api_base_url,
            api_key=api_key,
            session_id=session_id,
            page_name=page_name,
            group_fields=step2_fields,
            query=conversation,
            method=method,
            is_last=True,  # 标记为最后一步
            memory_rounds=memory_rounds
        )

        if response2.get("code") == 200 or response2.get("success"):
            data2 = response2.get("data", {})
            step2 = data2.get("step", 2)
            result2 = data2.get("result", {})
            status2 = data2.get("status", "unknown")
            merged_fields = data2.get("merged_fields", {})
            elapsed_time2 = data2.get("elapsed_time", 0)
            client_elapsed_time2 = data2.get("client_elapsed_time", 0)

            print(f"\n✓ 步骤2成功 (第{step2}步, 状态: {status2})")
            print(f"  服务端用时: {elapsed_time2:.2f}s | 客户端用时: {client_elapsed_time2:.2f}s")
            print(f"\n提取到 {len(result2)} 个字段:")

            for field_name, field_data in result2.items():
                value = extract_field_value(field_data)
                print(f"  - {field_name}: {value}")

            if merged_fields:
                print(f"\n【合并后的所有字段】({len(merged_fields)}个)")
                for field_name, value in merged_fields.items():
                    print(f"  - {field_name}: {value}")

            results["steps"].append({
                "step": 2,
                "fields_count": len(result2),
                "merged_fields_count": len(merged_fields),
                "status": "success",
                "elapsed_time": elapsed_time2,
                "client_elapsed_time": client_elapsed_time2
            })
            results["final_result"] = {
                "step2_fields": result2,
                "merged_fields": merged_fields
            }
        else:
            print(f"✗ 步骤2失败: {response2.get('message', '未知错误')}")
            results["steps"].append({"step": 2, "status": "failed", "error": response2.get('message')})

    except Exception as e:
        print(f"✗ 步骤2异常: {e}")
        results["steps"].append({"step": 2, "status": "error", "error": str(e)})

    # ========== 获取完整结果 ==========
    print("\n" + "=" * 80)
    print("【获取完整结果】")
    print("=" * 80)

    try:
        final_response = get_step_result(api_base_url, api_key, session_id)
        if final_response.get("code") == 200 or final_response.get("success"):
            final_data = final_response.get("data", {})
            print(f"✓ 获取完整结果成功")
            print(f"  - 总步骤数: {final_data.get('total_steps', 0)}")
            print(f"  - 状态: {final_data.get('status', 'unknown')}")
            results["full_result"] = final_data
        else:
            print(f"✗ 获取完整结果失败: {final_response.get('message', '未知错误')}")
    except Exception as e:
        print(f"✗ 获取完整结果异常: {e}")

    print("\n" + "=" * 80)
    print("测试完成!")
    print("=" * 80)

    return results


def main():
    parser = argparse.ArgumentParser(description="分步LLM填单测试")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API Key")
    parser.add_argument("--base-url", default=DEFAULT_API_BASE_URL, help="API基础URL")
    parser.add_argument("--page-name", default=PAGE_NAME, help="页面名称")
    parser.add_argument("--session-id", help="会话ID（不指定则自动生成）")
    parser.add_argument("--method", choices=[
        "with_structured_output", "bind_tools_non_stream", "bind_tools_stream",
        "custom_fc_non_stream", "custom_fc_stream", "pydantic_parser", "json_parser", "plain"
    ], help="LLM调用方法")
    parser.add_argument("--memory-rounds", type=int, default=0, help="保留历史消息的轮数")
    parser.add_argument("--conversation-file", help="对话内容文件路径")
    parser.add_argument("--output", help="输出结果到JSON文件")
    args = parser.parse_args()

    # 生成或获取session_id
    session_id = args.session_id or f"test_{uuid.uuid4().hex[:12]}"

    # 读取对话内容
    if args.conversation_file:
        with open(args.conversation_file, 'r', encoding='utf-8') as f:
            conversation = f.read()
    else:
        conversation = TEST_CONVERSATION

    # 运行测试
    results = run_step_test(
        api_base_url=args.base_url,
        api_key=args.api_key,
        page_name=args.page_name,
        session_id=session_id,
        conversation=conversation,
        method=args.method,
        memory_rounds=args.memory_rounds
    )

    # 保存结果
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {args.output}")

    return results


if __name__ == "__main__":
    main()
