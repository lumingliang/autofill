#!/usr/bin/env python3
"""
事件类型分级查询接口测试脚本
"""
import requests
import json
import uuid

# 配置
API_BASE_URL = "http://127.0.0.1:9999/api/v1/open"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"  # 实际的 API Key

# 请求头
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}


def test_event_type_query():
    """测试事件类型分级查询接口"""
    # 生成测试数据
    test_data = {
        "query": "我的手机坏了，屏幕黑屏无法开机",
        "session_id_prefix": "test",
        "system_prompt_name": "事件类型"
    }

    print("=" * 60)
    print("事件类型分级查询接口测试")
    print("=" * 60)
    print(f"\n请求URL: {API_BASE_URL}/event-type-query")
    print(f"\n请求参数:")
    print(json.dumps(test_data, ensure_ascii=False, indent=2))

    try:
        # 发送请求
        response = requests.post(
            f"{API_BASE_URL}/event-type-query",
            headers=headers,
            json=test_data,
            timeout=60
        )

        print(f"\n响应状态码: {response.status_code}")
        print(f"\n响应内容:")
        response_data = response.json()
        print(json.dumps(response_data, ensure_ascii=False, indent=2))

        # 验证响应
        if response.status_code == 200:
            if response_data.get("code") == 200:
                print(f"\n✅ 测试通过！")
                data = response_data.get("data", {})
                print(f"   一级事件类型: {data.get('一级事件类型', 'N/A')}")
                print(f"   二三级事件类型结果: {data.get('二三级事件类型结果', 'N/A')[:100]}...")
                return True, data
            else:
                print(f"\n❌ 测试失败: {response_data.get('message')}")
                return False, {}
        else:
            print(f"\n❌ HTTP错误: {response.status_code}")
            return False, {}

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求异常: {e}")
        return False, {}
    except json.JSONDecodeError:
        print(f"\n❌ JSON解析错误")
        return False, {}


def test_multiple_cases():
    """测试多个不同的查询内容"""
    test_cases = [
        {
            "name": "手机故障",
            "query": "我的手机坏了，屏幕黑屏无法开机"
        },
        {
            "name": "产品质量问题",
            "query": "买的电视有质量问题，画面有条纹，声音也不正常"
        },
        {
            "name": "服务态度投诉",
            "query": "去店里维修，工作人员态度很差，等了半天没人理"
        },
        {
            "name": "退换货咨询",
            "query": "买的东西不喜欢，想退货，请问怎么操作"
        },
        {
            "name": "功能咨询",
            "query": "这个产品怎么使用，有哪些功能"
        }
    ]

    print("\n" + "=" * 60)
    print("批量测试 - 事件类型分级查询")
    print("=" * 60)

    for case in test_cases:
        print(f"\n【{case['name']}】")
        print(f"查询内容: {case['query']}")

        test_data = {
            "query": case['query'],
            "session_id_prefix": "test"
        }

        try:
            response = requests.post(
                f"{API_BASE_URL}/event-type-query",
                headers=headers,
                json=test_data,
                timeout=60
            )

            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("code") == 200:
                    data = response_data.get("data", {})
                    print(f"✅ 一级事件类型: {data.get('一级事件类型', 'N/A')}")
                    llm_res = data.get('llm_res', '')
                    if llm_res:
                        print(f"   LLM结果: {llm_res[:80]}...")
                else:
                    print(f"❌ 失败: {response_data.get('message')}")
            else:
                print(f"❌ HTTP错误: {response.status_code}")

        except Exception as e:
            print(f"❌ 异常: {e}")


if __name__ == "__main__":
    # 测试单个请求
    print("\n" + "=" * 60)
    print("开始测试")
    print("=" * 60)

    success, data = test_event_type_query()

    # 批量测试
    test_multiple_cases()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
