#!/usr/bin/env python3
"""
反馈内容总结接口测试脚本
"""
import requests
import json
import uuid

# 配置
API_BASE_URL = "http://127.0.0.1:9999/api"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"  # 实际的 API Key

# 请求头
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}


def test_summary_feedback():
    """测试反馈内容总结接口"""

    # 生成测试数据
    test_data = {
        "order_id": f"ORDER_{uuid.uuid4().hex[:8].upper()}",
        "brand": "测试品牌",
        "feedback_content": "客户反馈：产品使用过程中遇到了几个问题，首先是APP连接不稳定，经常断连；其次是说明书描述不清楚，很多功能找不到在哪里设置；另外希望能够增加一个定时功能，这样使用起来会更方便。",
        "callback": "回调测试数据"
    }

    print("=" * 60)
    print("反馈内容总结接口测试")
    print("=" * 60)
    print(f"\n请求URL: {API_BASE_URL}/autofill/summary-feedback")
    print(f"\n请求参数:")
    print(json.dumps(test_data, ensure_ascii=False, indent=2))

    try:
        # 发送请求
        response = requests.post(
            f"{API_BASE_URL}/autofill/summary-feedback",
            headers=headers,
            json=test_data,
            timeout=30
        )

        print(f"\n响应状态码: {response.status_code}")
        print(f"\n响应内容:")
        response_data = response.json()
        print(json.dumps(response_data, ensure_ascii=False, indent=2))

        # 验证响应
        if response.status_code == 200:
            if response_data.get("code") == 200:
                print("\n✅ 测试通过！")
                data = response_data.get("data", {})
                print(f"   工单ID: {data.get('order_id')}")
                print(f"   总结结果: {data.get('summary')}")
            else:
                print(f"\n❌ 测试失败: {response_data.get('message')}")
        else:
            print(f"\n❌ HTTP错误: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求异常: {e}")
    except json.JSONDecodeError:
        print(f"\n❌ JSON解析错误")


if __name__ == "__main__":
    test_summary_feedback()
