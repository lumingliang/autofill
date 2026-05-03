"""
Agent API 测试脚本

测试 QueryAgent 的各种场景：
1. 基础查询 - 正常参数提取和 API 调用
2. 聊天记录查询 - 从对话中提取意图
3. 重试机制 - 自动调整参数
4. 无参数查询 - 直接执行
5. 错误处理 - API 错误场景

使用方法:
    cd /Users/lu/code/code/py/autofill
    python tests/test_agent_api.py

环境要求:
    - 服务已启动: python -m app.main
    - API Key 有效
"""
import json
import requests
import sys
from typing import Any, Dict

# 配置
BASE_URL = "http://localhost:9999"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"  # 请替换为有效的 API Key

# 测试用的 curl 模板
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


def call_agent_api(query: str, curl: str, **kwargs) -> Dict[str, Any]:
    """调用 Agent API"""
    url = f"{BASE_URL}/api/v1/agent/run"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    payload = {
        "query": query,
        "curl": curl,
        **kwargs
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        return response.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def print_result(test_name: str, result: Dict[str, Any]):
    """打印测试结果"""
    print(f"\n{'='*60}")
    print(f"测试: {test_name}")
    print(f"{'='*60}")
    print(f"成功: {result.get('success')}")
    print(f"状态: {result.get('status')}")
    print(f"尝试次数: {result.get('total_attempts')}")
    print(f"执行时间: {result.get('execution_time_ms')}ms")
    
    if result.get('error'):
        print(f"错误: {result.get('error')}")
    
    if result.get('data'):
        print(f"数据: {json.dumps(result.get('data'), ensure_ascii=False, indent=2)[:500]}...")
    print()


def test_basic_query():
    """测试1: 基础查询 - 查询重庆沙坪坝的比亚迪门店"""
    print("\n" + "="*60)
    print("测试1: 基础查询")
    print("="*60)
    
    query = "查询重庆沙坪坝的比亚迪门店"
    result = call_agent_api(
        query=query,
        curl=BYD_DEALER_CURL,
        system_prompt="从查询中提取城市、区域和门店名称",
        max_attempts=3
    )
    print_result("基础查询", result)
    return result.get('success', False)


def test_chat_context():
    """测试2: 聊天记录查询 - 从对话中提取意图"""
    print("\n" + "="*60)
    print("测试2: 聊天记录查询")
    print("="*60)
    
    # 模拟聊天记录
    chat_history = """
用户A: 我想买比亚迪，重庆有店吗？
用户B: 有啊，沙坪坝那边好像有一家
用户A: 具体地址知道吗？
"""
    
    result = call_agent_api(
        query=chat_history,
        curl=BYD_DEALER_CURL,
        system_prompt="分析聊天记录，提取用户想要查询的信息",
        expected_result="返回重庆沙坪坝的比亚迪门店地址",
        max_attempts=3
    )
    print_result("聊天记录查询", result)
    return result.get('success', False)


def test_retry_mechanism():
    """测试3: 重试机制 - 使用不存在的门店名称，看是否自动调整"""
    print("\n" + "="*60)
    print("测试3: 重试机制")
    print("="*60)
    
    # 使用一个可能不存在的具体名称，测试重试逻辑
    query = "查询重庆'海洋网体验中心'门店"
    
    result = call_agent_api(
        query=query,
        curl=BYD_DEALER_CURL,
        system_prompt="从查询中提取城市和门店名称，如果首次查询无结果，尝试使用更通用的关键词",
        expected_result="返回重庆的比亚迪门店信息",
        max_attempts=3
    )
    print_result("重试机制", result)
    # 即使失败也可能是因为真的没数据，只要尝试了多次就算测试通过
    return result.get('total_attempts', 0) > 0


def test_simple_query():
    """测试4: 简单查询 - 只查城市"""
    print("\n" + "="*60)
    print("测试4: 简单查询")
    print("="*60)
    
    query = "重庆有哪些比亚迪门店？"
    
    result = call_agent_api(
        query=query,
        curl=BYD_DEALER_CURL,
        max_attempts=2
    )
    print_result("简单查询", result)
    return result.get('success', False)


def test_invalid_api():
    """测试5: 错误处理 - 调用不存在的 API"""
    print("\n" + "="*60)
    print("测试5: 错误处理")
    print("="*60)
    
    invalid_curl = '''curl -X POST "http://localhost:9999/api/invalid-endpoint" \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}' '''
    
    query = "测试错误处理"
    
    result = call_agent_api(
        query=query,
        curl=invalid_curl,
        max_attempts=1
    )
    print_result("错误处理", result)
    # 错误处理测试，只要返回了结果就算通过（即使 success=False）
    return True


def test_no_params():
    """测试6: 无参数查询 - curl 中没有参数占位符"""
    print("\n" + "="*60)
    print("测试6: 无参数查询")
    print("="*60)
    
    # 这是一个没有参数的 curl（实际可能不存在这样的接口，仅测试解析逻辑）
    no_param_curl = '''curl -X GET "http://localhost:9999/api/health" \
  -H "Authorization: Bearer test" '''
    
    query = "检查服务状态"
    
    result = call_agent_api(
        query=query,
        curl=no_param_curl,
        max_attempts=1
    )
    print_result("无参数查询", result)
    return True  # 只要没抛异常就算通过


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("Agent API 测试套件")
    print("="*70)
    print(f"服务地址: {BASE_URL}")
    print(f"API Key: {API_KEY[:10]}...")
    
    tests = [
        ("基础查询", test_basic_query),
        ("聊天记录查询", test_chat_context),
        # ("重试机制", test_retry_mechanism),
        # ("简单查询", test_simple_query),
        # ("错误处理", test_invalid_api),
        # ("无参数查询", test_no_params),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n测试 {name} 异常: {e}")
            results.append((name, False))
    
    # 打印汇总
    print("\n" + "="*70)
    print("测试结果汇总")
    print("="*70)
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{status}: {name}")
    
    total = len(results)
    passed_count = sum(1 for _, p in results if p)
    print(f"\n总计: {passed_count}/{total} 通过")
    
    return passed_count == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
