"""
Agent API 简化测试脚本
"""
import json
import requests
import sys

BASE_URL = "http://localhost:9999"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"

BYD_DEALER_CURL = '''curl -X POST "http://localhost:9999/api/byd-dealers/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -d '{
    "app_key": "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR",
    "name": "{name}",
    "city": "{city}",
    "address": "{address}",
    "limit": 5
  }' '''


def test_basic_query():
    """测试基础查询"""
    url = f"{BASE_URL}/api/v1/agent/run"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    payload = {
        "query": "查询重庆沙坪坝的比亚迪门店",
        "curl": BYD_DEALER_CURL,
        "system_prompt": "从查询中提取城市、区域和门店名称",
        "max_attempts": 2
    }

    print(f"\n发送请求到: {url}")
    print(f"请求体: {json.dumps(payload, ensure_ascii=False, indent=2)}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        result = response.json()

        print(f"\n响应状态: {response.status_code}")
        print(f"响应结果:")
        print(f"  success: {result.get('success')}")
        print(f"  status: {result.get('status')}")
        print(f"  total_attempts: {result.get('total_attempts')}")
        print(f"  execution_time_ms: {result.get('execution_time_ms')}")
        print(f"  error: {result.get('error')}")

        if result.get('data'):
            print(f"  data: {json.dumps(result.get('data'), ensure_ascii=False, indent=2)[:500]}...")

        return result.get('success', False)
    except Exception as e:
        print(f"请求失败: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("Agent API 简化测试")
    print("="*60)

    success = test_basic_query()

    print(f"\n测试结果: {'通过' if success else '失败'}")
    sys.exit(0 if success else 1)
