#!/usr/bin/env python3
"""
Agent 测试脚本 - 模拟客服查询经销商

测试场景：
1. 直接搜索经销商接口
2. Agent 从对话中提取参数并查询
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.utils.agent_test_utils import AgentTestClient, run_test_case, print_test_header


def test_direct_dealer_search():
    """直接测试经销商搜索接口"""
    client = AgentTestClient()
    return client.search_dealers(
        name="海洋网",
        city="重庆",
        address="沙坪坝",
        limit=5
    )


def test_agent_dealer_query():
    """测试 Agent 查询经销商"""
    client = AgentTestClient()

    # 模拟客服聊天记录
    chat_history = """用户: 你好，我想问一下重庆有没有比亚迪的4S店？
客服: 您好，重庆有多家比亚迪门店，请问您在重庆哪个区呢？
用户: 我在沙坪坝区，想看看海洋网系列的
客服: 好的，我帮您查询一下重庆沙坪坝区的海洋网门店..."""

    return client.query_agent(query=chat_history)


def main():
    """主函数"""
    print_test_header("Agent 经销商查询测试")

    # 运行测试
    results = [
        run_test_case("直接搜索经销商", test_direct_dealer_search),
        run_test_case("Agent 查询经销商", test_agent_dealer_query),
    ]

    # 打印总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    passed = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)

    for result in results:
        status = "✅ 通过" if result.success else "❌ 失败"
        print(f"  {result.name}: {status}")

    print(f"\n总计: {passed} 通过, {failed} 失败")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
