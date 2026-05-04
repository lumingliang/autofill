"""
测试 DataQueryAgent V2 - 使用 Mock LLM
"""
import asyncio
import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.services.agent_v2.data_query_agent import DataQueryAgent, AgentDecision


async def test_agent_with_mock():
    """使用 Mock LLM 测试 DataQueryAgent"""
    print("=" * 60)
    print("测试 DataQueryAgent V2 (使用 Mock LLM)")
    print("=" * 60)

    # 定义 OpenAPI 规范
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "version": "1.0.0"
        },
        "servers": [
            {"url": "https://jsonplaceholder.typicode.com"}
        ],
        "paths": {
            "/posts/{id}": {
                "get": {
                    "operationId": "getPost",
                    "summary": "获取文章",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"}
                        }
                    ]
                }
            }
        }
    }

    # 将 spec 转为 JSON 字符串
    spec_str = json.dumps(openapi_spec)

    print("\n1. 初始化 DataQueryAgent...")
    agent = DataQueryAgent(
        openapi_spec=spec_str,
        max_iterations=2
    )
    print(f"   ✓ Agent 初始化成功")
    print(f"   - 可用工具: {agent.get_available_tools()}")

    # Mock LLM 响应 - 模拟工具调用
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "agent_decision": "complete",
        "formatted_result": "文章 ID: 1, 标题: sunt aut facere...",
        "reasoning": "成功获取文章数据"
    })
    mock_response.tool_calls = [
        {
            "name": "getPost",
            "args": {"id": 1}
        }
    ]

    print("\n2. 测试 Agent 查询 (Mock)...")

    # 使用 patch 替换 _create_llm 方法
    with patch.object(agent, '_create_llm') as mock_create_llm:
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_create_llm.return_value = mock_llm

        result = await agent.query("获取 ID 为 1 的文章")

        print(f"   ✓ 查询完成!")
        print(f"   - 决策: {result.agent_decision}")
        print(f"   - 理由: {result.reasoning}")
        print(f"   - 执行时间: {result.execution_time_ms}ms")
        print(f"   - 迭代次数: {len(result.iterations)}")

        if result.iterations:
            iteration = result.iterations[0]
            print(f"\n   第一轮迭代:")
            print(f"   - 工具名称: {iteration.tool_name}")
            print(f"   - 工具参数: {iteration.tool_params}")
            print(f"   - API 响应: {str(iteration.api_response)[:100]}..." if iteration.api_response else "   - API 响应: None")

        # 验证结果
        assert result.agent_decision == AgentDecision.COMPLETE, f"期望 complete, 实际 {result.agent_decision}"
        assert len(result.iterations) == 1, f"期望 1 轮迭代, 实际 {len(result.iterations)}"
        assert result.iterations[0].tool_name == "getPost", f"期望工具 getPost, 实际 {result.iterations[0].tool_name}"

        return True


async def test_agent_decision_parsing():
    """测试决策解析"""
    print("\n" + "=" * 60)
    print("测试决策解析")
    print("=" * 60)

    openapi_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0.0"},
        "servers": [{"url": "https://example.com"}],
        "paths": {}
    }

    agent = DataQueryAgent(openapi_spec=json.dumps(openapi_spec))

    test_cases = [
        # (输入, 期望结果)
        ('{"agent_decision": "complete", "reasoning": "ok"}', {"agent_decision": "complete", "reasoning": "ok"}),
        ('```json\n{"agent_decision": "continue", "reasoning": "more"}\n```', {"agent_decision": "continue", "reasoning": "more"}),
        ('{"agent_decision": "need_more_info", "formatted_result": null, "reasoning": "missing"}', {"agent_decision": "need_more_info", "reasoning": "missing"}),
        ('', {}),
        ('invalid json', {}),
    ]

    for input_str, expected in test_cases:
        result = agent._parse_decision(input_str)
        print(f"   输入: {input_str[:50]}...")
        print(f"   结果: {result}")

        if expected:
            assert result.get("agent_decision") == expected.get("agent_decision"), f"决策不匹配"
        print()

    print("   ✓ 决策解析测试通过")
    return True


async def main():
    """运行所有测试"""
    results = []

    try:
        results.append(("Agent 查询 (Mock)", await test_agent_with_mock()))
    except Exception as e:
        print(f"\n✗ Agent 查询测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Agent 查询 (Mock)", False))

    try:
        results.append(("决策解析", await test_agent_decision_parsing()))
    except Exception as e:
        print(f"\n✗ 决策解析测试失败: {e}")
        results.append(("决策解析", False))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"  {status}: {name}")

    all_passed = all(success for _, success in results)
    print("=" * 60)
    if all_passed:
        print("✓ 所有测试通过!")
    else:
        print("✗ 部分测试失败")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
