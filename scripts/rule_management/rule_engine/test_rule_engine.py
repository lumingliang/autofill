#!/usr/bin/env python3
"""
规则引擎完整测试脚本
测试场景：
1. 单任务选择题（plain方法，带filter）
2. 单任务填空题（plain方法，带filter）
3. 多任务混合（json_parser方法）
4. 多步填单流程
"""

import requests
import json
import uuid
from typing import Dict, Any

# 配置
BASE_URL = "http://localhost:9999"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"  # 请替换为实际的API Key

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}


def test_single_choice_with_filter():
    """测试场景1：单任务选择题（plain方法，带filter）"""
    print("\n" + "="*60)
    print("【测试场景1】单任务选择题（plain方法，带filter）")
    print("="*60)

    payload = {
        "session_id": f"test_{uuid.uuid4().hex[:8]}",
        "query": "我买的手机屏幕碎了，我要投诉",
        "method": "plain",
        "temperature": 0.7,
        "step": 1,
        "is_last": True,
        "params": [
            {
                "rule_name": "event_type",
                "prompt": {
                    "type": "choice",
                    "filter": {"一级事件类型": "投诉"},
                    "name_separator": " - ",
                    "select_fields": ["二级事件类型id", "三级事件类型id"],
                    "name_fields": ["二级事件类型", "三级事件类型"],
                    "rule_fields": ["二级事件类型填写规则", "三级事件类型填写规则"]
                }
            }
        ]
    }

    response = requests.post(
        f"{BASE_URL}/api/autofill/llm/rule/execute",
        headers=HEADERS,
        json=payload
    )

    print(f"请求参数：\n{json.dumps(payload, ensure_ascii=False, indent=2)}")
    print(f"\n响应结果：\n{json.dumps(response.json(), ensure_ascii=False, indent=2)}")

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "results" in data["data"]
    assert "event_type" in data["data"]["results"]
    print("✅ 测试通过")
    return data


def test_single_text_with_filter():
    """测试场景2：单任务填空题（plain方法，带filter）"""
    print("\n" + "="*60)
    print("【测试场景2】单任务填空题（plain方法，带filter）")
    print("="*60)

    payload = {
        "session_id": f"test_{uuid.uuid4().hex[:8]}",
        "query": "我买的手机屏幕碎了，我要投诉",
        "method": "plain",
        "temperature": 0.7,
        "step": 1,
        "is_last": True,
        "params": [
            {
                "rule_name": "reply_template",
                "prompt": {
                    "type": "text",
                    "filter": {"模板名称": "手机屏幕破损回复"},
                    "select_fields": ["模板id", "适用场景"],
                    "name_fields": ["模板名称"],
                    "rule_fields": ["模板填写规则"]
                }
            }
        ]
    }

    response = requests.post(
        f"{BASE_URL}/api/autofill/llm/rule/execute",
        headers=HEADERS,
        json=payload
    )

    print(f"请求参数：\n{json.dumps(payload, ensure_ascii=False, indent=2)}")
    print(f"\n响应结果：\n{json.dumps(response.json(), ensure_ascii=False, indent=2)}")

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "results" in data["data"]
    assert "reply_template" in data["data"]["results"]
    print("✅ 测试通过")
    return data


def test_multi_task_json_parser():
    """测试场景3：多任务混合（json_parser方法）"""
    print("\n" + "="*60)
    print("【测试场景3】多任务混合（json_parser方法）")
    print("="*60)

    payload = {
        "session_id": f"test_{uuid.uuid4().hex[:8]}",
        "query": "我买的手机电池鼓包了，太危险了！",
        "method": "json_parser",
        "temperature": 0.3,
        "step": 1,
        "is_last": True,
        "params": [
            {
                "rule_name": "event_type",
                "prompt": {
                    "type": "choice",
                    "filter": {"一级事件类型": "投诉"},
                    "name_separator": " - ",
                    "select_fields": ["一级事件类型id", "二级事件类型id", "三级事件类型id"],
                    "name_fields": ["二级事件类型", "三级事件类型"],
                    "rule_fields": ["二级事件类型填写规则", "三级事件类型填写规则"]
                }
            },
            {
                "rule_name": "reply_template",
                "prompt": {
                    "type": "text",
                    "filter": {"模板名称": "商品质量问题回复"},
                    "select_fields": ["模板id", "适用场景"],
                    "name_fields": ["模板名称"],
                    "rule_fields": ["模板填写规则"]
                }
            }
        ]
    }

    response = requests.post(
        f"{BASE_URL}/api/autofill/llm/rule/execute",
        headers=HEADERS,
        json=payload
    )

    print(f"请求参数：\n{json.dumps(payload, ensure_ascii=False, indent=2)}")
    print(f"\n响应结果：\n{json.dumps(response.json(), ensure_ascii=False, indent=2)}")

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "results" in data["data"]
    assert "event_type" in data["data"]["results"]
    assert "reply_template" in data["data"]["results"]
    print("✅ 测试通过")
    return data


def test_multi_step_fill():
    """测试场景4：多步填单流程"""
    print("\n" + "="*60)
    print("【测试场景4】多步填单流程")
    print("="*60)

    session_id = f"test_multi_{uuid.uuid4().hex[:8]}"

    # 第1步：事件分类
    print("\n--- 第1步：事件分类 ---")
    payload1 = {
        "session_id": session_id,
        "query": "我买的手机屏幕碎了，我要投诉",
        "method": "plain",
        "temperature": 0.7,
        "step": 1,
        "is_last": False,
        "params": [
            {
                "rule_name": "event_type",
                "prompt": {
                    "type": "choice",
                    "filter": {"一级事件类型": "投诉"},
                    "name_separator": " - ",
                    "select_fields": ["二级事件类型id", "三级事件类型id"],
                    "name_fields": ["二级事件类型", "三级事件类型"],
                    "rule_fields": ["二级事件类型填写规则", "三级事件类型填写规则"]
                }
            }
        ]
    }

    response1 = requests.post(
        f"{BASE_URL}/api/autofill/llm/rule/execute",
        headers=HEADERS,
        json=payload1
    )

    print(f"请求参数：\n{json.dumps(payload1, ensure_ascii=False, indent=2)}")
    print(f"\n响应结果：\n{json.dumps(response1.json(), ensure_ascii=False, indent=2)}")

    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["code"] == 200
    assert data1["data"]["status"] == "processing"
    print("✅ 第1步通过")

    # 第2步：生成回复（最后一步）
    print("\n--- 第2步：生成回复 ---")
    payload2 = {
        "session_id": session_id,
        "query": "我买的手机屏幕碎了，我要投诉",
        "method": "plain",
        "temperature": 0.7,
        "step": 2,
        "is_last": True,
        "params": [
            {
                "rule_name": "reply_template",
                "prompt": {
                    "type": "text",
                    "filter": {"模板名称": "手机屏幕破损回复"},
                    "select_fields": ["模板id", "模板内容", "适用场景"],
                    "name_fields": ["模板名称"],
                    "rule_fields": ["模板填写规则"]
                }
            }
        ]
    }

    response2 = requests.post(
        f"{BASE_URL}/api/autofill/llm/rule/execute",
        headers=HEADERS,
        json=payload2
    )

    print(f"请求参数：\n{json.dumps(payload2, ensure_ascii=False, indent=2)}")
    print(f"\n响应结果：\n{json.dumps(response2.json(), ensure_ascii=False, indent=2)}")

    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["code"] == 200
    assert data2["data"]["status"] == "completed"
    print("✅ 第2步通过")

    # 查询完整结果
    print("\n--- 查询完整结果 ---")
    result_response = requests.post(
        f"{BASE_URL}/api/autofill/llm/rule/execute/result",
        headers=HEADERS,
        json={"session_id": session_id}
    )

    print(f"\n完整结果：\n{json.dumps(result_response.json(), ensure_ascii=False, indent=2)}")

    assert result_response.status_code == 200
    result_data = result_response.json()
    assert result_data["code"] == 200
    assert "merged_fields" in result_data["data"]
    print("✅ 多步填单测试通过")

    return result_data


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始规则引擎测试")
    print("="*60)

    try:
        # 测试1：单任务选择题
        test_single_choice_with_filter()

        # 测试2：单任务填空题
        test_single_text_with_filter()

        # 测试3：多任务混合
        test_multi_task_json_parser()

        # 测试4：多步填单
        test_multi_step_fill()

        print("\n" + "="*60)
        print("✅ 所有测试通过！")
        print("="*60)

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")


def print_usage():
    """打印使用说明"""
    print("用法: python test_rule_engine.py [测试编号]")
    print("")
    print("测试编号:")
    print("  1  - 单任务选择题（plain方法，带filter）")
    print("  2  - 单任务填空题（plain方法，带filter）")
    print("  3  - 多任务混合（json_parser方法）")
    print("  4  - 多步填单流程")
    print("  all - 运行所有测试（默认）")
    print("")
    print("示例:")
    print("  python test_rule_engine.py        # 运行所有测试")
    print("  python test_rule_engine.py 1      # 只运行测试1")
    print("  python test_rule_engine.py 3      # 只运行测试3")


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1 or sys.argv[1] == "all":
        # 运行所有测试
        run_all_tests()
    elif sys.argv[1] in ["1", "2", "3", "4"]:
        # 运行指定测试
        test_num = sys.argv[1]
        print("\n" + "="*60)
        print(f"开始运行测试 {test_num}")
        print("="*60)

        try:
            if test_num == "1":
                test_single_choice_with_filter()
            elif test_num == "2":
                test_single_text_with_filter()
            elif test_num == "3":
                test_multi_task_json_parser()
            elif test_num == "4":
                test_multi_step_fill()

            print("\n" + "="*60)
            print(f"✅ 测试 {test_num} 通过！")
            print("="*60)

        except AssertionError as e:
            print(f"\n❌ 测试失败: {e}")
        except Exception as e:
            print(f"\n❌ 测试异常: {e}")
    else:
        print_usage()
