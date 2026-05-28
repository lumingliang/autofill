#!/usr/bin/env python3
"""
反馈内容总结接口测试脚本
使用规则引擎模式
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
    print("反馈内容总结接口测试 - 规则引擎模式")
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
                print(f"\n✅ 测试通过！")
                data = response_data.get("data", {})
                summary = data.get('summary', '')
                print(f"   工单ID: {data.get('order_id')}")
                print(f"   总结结果: {summary}")
                print(f"   总结字数: {len(summary)} 字")
                
                # 检查是否控制在35字以内
                if len(summary) <= 35:
                    print(f"   ✅ 字数符合要求（≤35字）")
                else:
                    print(f"   ⚠️ 字数超出限制（>35字）")
                    
                return True, summary
            else:
                print(f"\n❌ 测试失败: {response_data.get('message')}")
                return False, ""
        else:
            print(f"\n❌ HTTP错误: {response.status_code}")
            return False, ""

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求异常: {e}")
        return False, ""
    except json.JSONDecodeError:
        print(f"\n❌ JSON解析错误")
        return False, ""


def test_multiple_cases():
    """测试多个不同的反馈内容"""
    test_cases = [
        {
            "name": "产品问题反馈",
            "content": "客户反馈：产品使用过程中遇到了几个问题，首先是APP连接不稳定，经常断连；其次是说明书描述不清楚，很多功能找不到在哪里设置；另外希望能够增加一个定时功能，这样使用起来会更方便。"
        },
        {
            "name": "服务态度投诉",
            "content": "今天去4S店保养，服务人员态度非常差，等了两个小时才有人接待，而且解释问题很不耐烦，希望改进服务质量。"
        },
        {
            "name": "质量问题反馈",
            "content": "刚买一个月的车，空调就不制冷了，去4S店修了两次还没好，要求退换车或者彻底解决问题。"
        }
    ]
    
    print("\n" + "=" * 60)
    print("批量测试 - 规则引擎模式")
    print("=" * 60)
    
    for case in test_cases:
        print(f"\n【{case['name']}】")
        print(f"反馈内容: {case['content'][:50]}...")
        
        test_data = {
            "order_id": f"ORDER_{uuid.uuid4().hex[:8].upper()}",
            "brand": "测试品牌",
            "feedback_content": case['content']
        }
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/autofill/summary-feedback",
                headers=headers,
                json=test_data,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("code") == 200:
                    summary = response_data.get("data", {}).get("summary", "")
                    print(f"✅ 总结: {summary}")
                    print(f"   字数: {len(summary)} 字 {'✅' if len(summary) <= 35 else '⚠️'}")
                else:
                    print(f"❌ 失败: {response_data.get('message')}")
            else:
                print(f"❌ HTTP错误: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 异常: {e}")


if __name__ == "__main__":
    # 测试规则引擎模式
    print("\n" + "=" * 60)
    print("开始测试")
    print("=" * 60)
    
    success, summary = test_summary_feedback()
    
    # 批量测试
    test_multiple_cases()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
