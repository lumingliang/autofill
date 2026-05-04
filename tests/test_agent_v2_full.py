"""
DataQueryAgent V2 完整流程测试

测试完整的 Agent 查询流程（需要 LLM 配置）。
"""
import asyncio
import json
import tempfile
import os

from app.services.agent_v2 import DataQueryAgent


# 测试用的 OpenAPI 规范
TEST_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "测试 API", "version": "1.0.0"},
    "servers": [{"url": "https://jsonplaceholder.typicode.com"}],
    "paths": {
        "/posts/{id}": {
            "get": {
                "operationId": "getPost",
                "summary": "获取文章",
                "description": "根据文章ID获取文章详情",
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                ]
            }
        },
        "/posts": {
            "get": {
                "operationId": "listPosts",
                "summary": "获取文章列表",
                "description": "获取所有文章列表，支持按用户ID过滤",
                "parameters": [
                    {"name": "userId", "in": "query", "required": False, "schema": {"type": "integer"}}
                ]
            }
        }
    }
}


async def test_agent_query():
    """测试 Agent 查询"""
    print("=" * 60)
    print("测试 DataQueryAgent 完整流程")
    print("=" * 60)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(TEST_SPEC, f)
        temp_file = f.name

    try:
        # 创建 Agent
        agent = DataQueryAgent(
            openapi_spec=temp_file,
            max_iterations=3,
            tenant_id=0,
            temperature=0.0
        )

        print(f"\n✓ Agent 创建成功")
        print(f"  可用工具: {agent.get_available_tools()}")

        # 测试 1: 简单查询
        print("\n" + "-" * 40)
        print("测试 1: 查询 ID 为 1 的文章")
        print("-" * 40)

        result = await agent.query("获取 ID 为 1 的文章")

        print(f"决策: {result.agent_decision}")
        print(f"理由: {result.reasoning}")
        print(f"执行时间: {result.execution_time_ms}ms")
        print(f"迭代次数: {len(result.iterations)}")

        if result.api_response:
            try:
                data = json.loads(result.api_response) if isinstance(result.api_response, str) else result.api_response
                if isinstance(data, dict):
                    print(f"文章标题: {data.get('title', 'N/A')[:50]}...")
            except:
                pass

        if result.formatted_result:
            print(f"格式化结果: {result.formatted_result[:100]}...")

        # 测试 2: 带过滤的查询
        print("\n" + "-" * 40)
        print("测试 2: 查询用户 1 的所有文章")
        print("-" * 40)

        result2 = await agent.query("获取用户ID为1的所有文章")

        print(f"决策: {result2.agent_decision}")
        print(f"理由: {result2.reasoning}")
        print(f"执行时间: {result2.execution_time_ms}ms")
        print(f"迭代次数: {len(result2.iterations)}")

        if result2.api_response:
            try:
                data = json.loads(result2.api_response) if isinstance(result2.api_response, str) else result2.api_response
                if isinstance(data, list):
                    print(f"返回数量: {len(data)} 条")
            except:
                pass

        # 测试 3: 显示迭代详情
        print("\n" + "-" * 40)
        print("测试 3: 迭代详情")
        print("-" * 40)

        for it in result.iterations:
            print(f"\n第 {it.round} 轮:")
            print(f"  工具: {it.tool_name}")
            print(f"  参数: {it.tool_params}")
            print(f"  决策: {it.agent_decision}")
            print(f"  理由: {it.reasoning[:100]}...")

        print("\n" + "=" * 60)
        print("✓ 所有测试完成")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        os.unlink(temp_file)


if __name__ == "__main__":
    asyncio.run(test_agent_query())
