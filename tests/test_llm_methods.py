"""
测试各种 LLM 方法类型
"""
import requests
import json

BASE_URL = "http://localhost:9999"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"

# 测试用的 curl 命令
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


def test_method(method_name: str, max_attempts: int = 2):
    """测试指定的方法"""
    print(f"\n{'='*60}")
    print(f"测试方法: {method_name}")
    print(f"{'='*60}")

    url = f"{BASE_URL}/api/v1/agent/run"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    payload = {
        "query": "查询重庆的比亚迪门店",
        "curl": BYD_DEALER_CURL,
        "system_prompt": "从查询中提取城市和门店名称",
        "max_attempts": max_attempts,
        "llm_method": method_name
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=None)
        result = response.json()

        print(f"响应状态: {response.status_code}")
        print(f"success: {result.get('success')}")
        print(f"status: {result.get('status')}")
        print(f"total_attempts: {result.get('total_attempts')}")
        print(f"execution_time_ms: {result.get('execution_time_ms')}")

        if result.get('error'):
            print(f"error: {result.get('error')}")

        data = result.get('data', {})
        if data and isinstance(data, dict):
            api_data = data.get('data', [])
            if api_data:
                print(f"找到 {len(api_data)} 条结果")
            else:
                print("未找到结果")

        if result.get('success'):
            print(f"✓ 方法 {method_name} 测试通过")
            return True
        else:
            print(f"✗ 方法 {method_name} 测试失败")
            return False

    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False


def main():
    """主函数"""
    print("开始测试各种 LLM 方法类型...")

    # 测试所有支持的方法
    # 注意: 只有支持 Function Calling 的方法才能正确处理多工具场景
    methods = [
        "bind_tools_stream",       # 推荐：LangChain 流式 Function Calling
        # "bind_tools_non_stream",   # 推荐：LangChain 非流式 Function Calling
        # "with_structured_output",  # LangChain 官方结构化输出
        # "custom_fc_non_stream",    # 推荐：自定义非流式 Function Calling
        # "custom_fc_stream",        # 推荐：自定义流式 Function Calling
        # 以下方法不支持多工具选择，仅用于兼容性测试
        # "pydantic_parser",
        # "json_parser"
    ]

    results = {}
    for method in methods:
        results[method] = test_method(method)

    # 汇总结果
    print(f"\n{'='*60}")
    print("测试结果汇总")
    print(f"{'='*60}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for method, success in results.items():
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{status}: {method}")

    print(f"\n总计: {passed}/{total} 通过")

    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
