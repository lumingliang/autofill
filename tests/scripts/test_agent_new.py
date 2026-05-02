"""
测试新的 Agent 架构

测试内容：
1. CurlParser 解析
2. QueryAgent 执行
3. API 接口调用
"""
import asyncio
import json

from app.services.agent import CurlParser, AgentInput, AgentContext, QueryAgent


def test_curl_parser():
    """测试 CurlParser"""
    print("=" * 60)
    print("测试 CurlParser")
    print("=" * 60)

    # 测试用例 1: POST JSON
    curl1 = """curl -X POST 'http://httpbin.org/post' -H 'Content-Type: application/json' -d '{"name": "test", "age": 25}'"""

    parsed1 = CurlParser.parse(curl1)
    print(f"\n测试 1 - POST JSON:")
    print(f"  URL: {parsed1.url}")
    print(f"  Method: {parsed1.method}")
    print(f"  Headers: {parsed1.headers}")
    print(f"  Body Params: {parsed1.body_params}")
    print(f"  Param Schemas: {[s.name for s in parsed1.param_schemas]}")

    assert parsed1.url == "http://httpbin.org/post"
    assert parsed1.method == "POST"
    assert "name" in parsed1.body_params
    assert "age" in parsed1.body_params
    print("  ✅ 通过")

    # 测试用例 2: GET with query params
    curl2 = """curl 'http://httpbin.org/get?foo=bar&baz=123'"""

    parsed2 = CurlParser.parse(curl2)
    print(f"\n测试 2 - GET with query:")
    print(f"  URL: {parsed2.url}")
    print(f"  Method: {parsed2.method}")
    print(f"  Query Params: {parsed2.query_params}")

    assert parsed2.method == "GET"
    assert parsed2.query_params.get("foo") == "bar"
    assert parsed2.query_params.get("baz") == 123  # 应该被推断为整数
    print("  ✅ 通过")

    # 测试用例 3: 复杂 curl
    curl3 = """curl -X POST 'https://api.example.com/search' \
        -H 'Authorization: Bearer token123' \
        -H 'Content-Type: application/json' \
        -d '{"keyword": "体验中心", "city": "上海", "page": 1, "size": 10}'"""

    parsed3 = CurlParser.parse(curl3)
    print(f"\n测试 3 - 复杂 curl:")
    print(f"  URL: {parsed3.url}")
    print(f"  Method: {parsed3.method}")
    print(f"  Headers: {list(parsed3.headers.keys())}")
    print(f"  Body Params: {parsed3.body_params}")
    print(f"  Param Schemas:")
    for schema in parsed3.param_schemas:
        print(f"    - {schema.name} ({schema.param_type}): {schema.description}")

    assert "keyword" in parsed3.body_params
    assert "city" in parsed3.body_params
    assert parsed3.body_params.get("page") == 1
    print("  ✅ 通过")

    print("\n✅ CurlParser 所有测试通过！")


async def test_query_agent_mock():
    """测试 QueryAgent（使用 mock API）"""
    print("\n" + "=" * 60)
    print("测试 QueryAgent")
    print("=" * 60)

    # 使用 httpbin 作为测试 API
    curl = """curl -X POST 'http://httpbin.org/post' -H 'Content-Type: application/json' -d '{"name": "test", "value": 123}'"""

    agent_input = AgentInput(
        query="测试查询",
        curl=curl,
        system_prompt="这是一个测试",
        max_attempts=1,
        timeout=10
    )

    context = AgentContext(tenant_id=0)
    agent = QueryAgent(context=context)

    print(f"\n执行 Agent...")
    print(f"  Query: {agent_input.query}")
    print(f"  Curl: {curl[:50]}...")

    try:
        result = await agent.run(agent_input)

        print(f"\n执行结果:")
        print(f"  Success: {result.success}")
        print(f"  Status: {result.status.value}")
        print(f"  Total Attempts: {result.total_attempts}")
        print(f"  Execution Time: {result.execution_time_ms}ms")

        if result.data:
            print(f"  Data: {json.dumps(result.data, indent=2)[:200]}...")

        if result.error:
            print(f"  Error: {result.error}")

        print("\n✅ QueryAgent 测试完成！")

    except Exception as e:
        print(f"\n❌ QueryAgent 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_build_curl():
    """测试重建 curl"""
    print("\n" + "=" * 60)
    print("测试重建 curl")
    print("=" * 60)

    curl = """curl -X POST 'http://api.example.com/search' -H 'Content-Type: application/json' -d '{"name": "test", "city": "上海"}'"""

    parsed = CurlParser.parse(curl)
    params = {"name": "体验中心", "city": "北京"}

    new_curl = CurlParser.build_curl(parsed, params)

    print(f"\n原始 curl:\n  {curl}")
    print(f"\n参数: {params}")
    print(f"\n重建 curl:\n  {new_curl}")

    assert "体验中心" in new_curl
    assert "北京" in new_curl
    print("\n✅ 重建 curl 测试通过！")


async def main():
    """主测试函数"""
    print("\n" + "🧪" * 30)
    print("开始测试新的 Agent 架构")
    print("🧪" * 30 + "\n")

    # 测试 CurlParser
    test_curl_parser()

    # 测试重建 curl
    test_build_curl()

    # 测试 QueryAgent
    await test_query_agent_mock()

    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
