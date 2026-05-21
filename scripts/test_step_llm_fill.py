#!/usr/bin/env python3
"""
分步LLM填单测试脚本 - 完整版
测试场景：基于session的分步填单流程，覆盖事件类型+服务记录类型的完整场景

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

    # 运行所有测试场景
    python test_step_llm_fill.py --test-all
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

# ========== 测试用例 ==========

# 测试用例1：道路救援场景（对应一级事件类型：道路救援）
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

# 测试用例2：保养预约场景（对应一级事件类型：保养预约）
TEST_CONVERSATION_MAINTENANCE = """
【第1轮】
客服：您好，比亚迪汽车客服中心，请问有什么可以帮您？
用户：我想预约一下车辆保养。

【第2轮】
客服：好的，请问您的车辆型号和车架号？
用户：比亚迪唐DM，车架号LGXC14EAXN7654321。

【第3轮】
客服：请问您想预约什么类型的保养？
用户：常规保养，小保养就行。

【第4轮】
客服：请问您方便到店的时间？
用户：下周三下午2点可以吗？

【第5轮】
客服：好的，请问您的联系电话？
用户：13987654321。
"""

# 测试用例3：质量问题投诉场景（对应一级事件类型：质量问题）
TEST_CONVERSATION_QUALITY = """
【第1轮】
客服：您好，比亚迪汽车客服中心，请问有什么可以帮您？
用户：我的车漆面有问题，新车就有色差。

【第2轮】
客服：非常抱歉给您带来困扰。请问您的车辆型号和车架号？
用户：比亚迪海豹，车架号LGXC14EAXN1112223。

【第3轮】
客服：请问漆面问题具体在什么部位？
用户：引擎盖和左前门，颜色明显不一样。

【第4轮】
客服：请问您什么时候发现这个问题的？
用户：提车的时候就发现了，但是当时没在意。

【第5轮】
客服：请问您的联系电话，我们安排专人跟进？
用户：13611112222。
"""

# 测试用例4：400电话场景
TEST_CONVERSATION_400 = """
【第1轮】
客服：您好，比亚迪400客服中心，请问有什么可以帮您？
用户：我的车仪表盘显示三级报警，是什么意思？

【第2轮】
客服：请问您的车辆型号和车架号？
用户：比亚迪宋Pro，车架号LGXC14EAXN4445556。

【第3轮】
客服：三级报警是动力电池系统故障，建议您立即停车检查。请问您现在的位置？
用户：我在高速公路上。

【第4轮】
客服：为了您的安全，请立即靠边停车并打开双闪。我们立即安排救援。请问您的联系电话？
用户：13733334444。
"""


def send_step_llm_fill_request(
    api_base_url: str,
    api_key: str,
    session_id: str,
    group_names: List[str],
    field_names: List[str],
    system_prompt_group: Optional[str],
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
        "group_names": group_names,
        "field_names": field_names,
        "system_prompt_group": system_prompt_group,
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


def run_step_test_scenario(
    api_base_url: str,
    api_key: str,
    session_id: str,
    conversation: str,
    scenario_name: str,
    method: str = None,
    memory_rounds: int = 0
) -> Dict:
    """
    运行分步测试场景

    步骤1: 获取一级事件类型和服务记录类型（主字段）
    步骤2: 同时获取二三级事件类型和服务记录模板字段
    """

    print("\n" + "=" * 80)
    print(f"【测试场景】{scenario_name}")
    print("=" * 80)
    print(f"Session ID: {session_id}")
    print(f"API Base URL: {api_base_url}")
    if method:
        print(f"使用方法: {method}")
    print("=" * 80)

    results = {
        "session_id": session_id,
        "scenario_name": scenario_name,
        "steps": [],
        "timestamp": datetime.now().isoformat()
    }

    # ========== 步骤1：获取一级事件类型和服务记录类型 ==========
    print("\n" + "-" * 80)
    print("【步骤1】获取一级事件类型和服务记录类型")
    print("-" * 80)

    try:
        response1 = send_step_llm_fill_request(
            api_base_url=api_base_url,
            api_key=api_key,
            session_id=session_id,
            group_names=["事件类型", "服务记录类型"],
            field_names=["一级事件类型", "服务记录类型"],
            system_prompt_group="事件类型",
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

    # ========== 步骤2：获取二三级事件类型和服务记录模板字段 ==========
    print("\n" + "-" * 80)
    print("【步骤2】获取二三级事件类型和服务记录模板字段")
    print("-" * 80)

    event_type = step1_extracted.get("一级事件类型", {}).get("label", "")
    service_type = step1_extracted.get("服务记录类型", {}).get("label", "")
    print(f"一级事件类型: {event_type}")
    print(f"服务记录类型: {service_type}")

    # 构建步骤2的字段组和字段名
    step2_group_names = []
    step2_field_names = []

    # 添加二三级事件类型字段
    if event_type:
        step2_group_names.append("事件类型")
        secondary_field_name = f"{event_type}-二三级事件类型"
        step2_field_names.append(secondary_field_name)
        print(f"请求次字段: {secondary_field_name}")

    # 添加服务记录模板字段组
    if service_type:
        group_name = f"服务记录-{service_type}"
        step2_group_names.append(group_name)
        print(f"请求字段组: {group_name}")

    if not step2_group_names:
        print("⚠ 无法确定步骤2字段，跳过")
        results["steps"].append({"step": 2, "status": "skipped", "reason": "无法确定字段"})
        return results

    try:
        response2 = send_step_llm_fill_request(
            api_base_url=api_base_url,
            api_key=api_key,
            session_id=session_id,
            group_names=step2_group_names,
            field_names=step2_field_names,
            system_prompt_group=step2_group_names[0] if step2_group_names else None,
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

            step2_extracted = {}
            for field_name, field_data in result2.items():
                value = extract_field_value(field_data)
                label = field_data.get("value", {}).get("label", value) if isinstance(field_data.get("value"), dict) else value
                step2_extracted[field_name] = {"value": value, "label": label}
                print(f"  - {field_name}: {label} ({value})")

            if merged_fields:
                print(f"\n【合并后的所有字段】({len(merged_fields)}个)")
                for field_name, value in merged_fields.items():
                    print(f"  - {field_name}: {value}")

            results["steps"].append({
                "step": 2,
                "fields": step2_extracted,
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
    print("\n" + "-" * 80)
    print("【获取完整结果】")
    print("-" * 80)

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
    print(f"【{scenario_name}】测试完成!")
    print("=" * 80)

    return results


def run_all_tests(
    api_base_url: str,
    api_key: str,
    method: str = None,
    memory_rounds: int = 0
) -> List[Dict]:
    """运行所有测试场景"""

    test_scenarios = [
        ("道路救援场景", TEST_CONVERSATION_RESCUE),
        ("保养预约场景", TEST_CONVERSATION_MAINTENANCE),
        ("质量问题场景", TEST_CONVERSATION_QUALITY),
        ("400电话场景", TEST_CONVERSATION_400),
    ]

    all_results = []

    print("\n" + "=" * 80)
    print("开始运行所有测试场景")
    print("=" * 80)

    for i, (scenario_name, conversation) in enumerate(test_scenarios, 1):
        session_id = f"test_{uuid.uuid4().hex[:12]}"

        result = run_step_test_scenario(
            api_base_url=api_base_url,
            api_key=api_key,
            session_id=session_id,
            conversation=conversation,
            scenario_name=scenario_name,
            method=method,
            memory_rounds=memory_rounds
        )

        all_results.append(result)

        # 场景之间添加间隔
        if i < len(test_scenarios):
            print(f"\n{'=' * 80}")
            print(f"场景 {i}/{len(test_scenarios)} 完成，准备下一个场景...")
            print(f"{'=' * 80}\n")

    # 汇总报告
    print("\n" + "=" * 80)
    print("所有测试场景执行完成")
    print("=" * 80)

    success_count = sum(1 for r in all_results if all(s.get("status") == "success" for s in r.get("steps", [])))
    total_count = len(all_results)

    print(f"\n汇总报告:")
    print(f"  总场景数: {total_count}")
    print(f"  完全成功: {success_count}")
    print(f"  部分失败: {total_count - success_count}")

    for result in all_results:
        scenario_name = result.get("scenario_name", "未知场景")
        steps = result.get("steps", [])
        step_status = [s.get("status", "unknown") for s in steps]
        status_icon = "✓" if all(s == "success" for s in step_status) else "✗"
        print(f"  {status_icon} {scenario_name}: {step_status}")

    return all_results


def main():
    parser = argparse.ArgumentParser(description="分步LLM填单测试")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API Key")
    parser.add_argument("--base-url", default=DEFAULT_API_BASE_URL, help="API基础URL")
    parser.add_argument("--session-id", help="会话ID（不指定则自动生成）")
    parser.add_argument("--method", choices=[
        "with_structured_output", "bind_tools_non_stream", "bind_tools_stream",
        "custom_fc_non_stream", "custom_fc_stream", "pydantic_parser", "json_parser", "plain"
    ], help="LLM调用方法")
    parser.add_argument("--memory-rounds", type=int, default=0, help="保留历史消息的轮数")
    parser.add_argument("--conversation-file", help="对话内容文件路径")
    parser.add_argument("--output", help="输出结果到JSON文件")
    parser.add_argument("--test-all", action="store_true", help="运行所有测试场景")
    parser.add_argument("--scenario", choices=["rescue", "maintenance", "quality", "400"], default="rescue",
                        help="选择测试场景（默认: rescue）")
    args = parser.parse_args()

    if args.test_all:
        # 运行所有测试场景
        results = run_all_tests(
            api_base_url=args.base_url,
            api_key=args.api_key,
            method=args.method,
            memory_rounds=args.memory_rounds
        )
    else:
        # 运行单个测试场景
        session_id = args.session_id or f"test_{uuid.uuid4().hex[:12]}"

        # 选择测试用例
        scenario_map = {
            "rescue": ("道路救援场景", TEST_CONVERSATION_RESCUE),
            "maintenance": ("保养预约场景", TEST_CONVERSATION_MAINTENANCE),
            "quality": ("质量问题场景", TEST_CONVERSATION_QUALITY),
            "400": ("400电话场景", TEST_CONVERSATION_400),
        }

        scenario_name, conversation = scenario_map.get(args.scenario, ("道路救援场景", TEST_CONVERSATION_RESCUE))

        # 读取对话内容（如果指定了文件）
        if args.conversation_file:
            with open(args.conversation_file, 'r', encoding='utf-8') as f:
                conversation = f.read()

        # 运行测试
        results = run_step_test_scenario(
            api_base_url=args.base_url,
            api_key=args.api_key,
            session_id=session_id,
            conversation=conversation,
            scenario_name=scenario_name,
            method=args.method,
            memory_rounds=args.memory_rounds
        )

        results = [results]  # 包装成列表以便统一处理

    # 保存结果
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {args.output}")

    return results


if __name__ == "__main__":
    main()
