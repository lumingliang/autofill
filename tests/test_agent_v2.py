"""
DataQueryAgent V2 测试脚本

测试 OpenAPI 解析、Tool 生成和 Agent 查询功能。
"""
import asyncio
import json
from typing import Dict, Any

import httpx

from app.services.agent_v2 import OpenAPIParser, APIToolManager, DataQueryAgent


# 测试用的简单 OpenAPI 规范
TEST_OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "测试 API",
        "version": "1.0.0",
        "description": "用于测试 DataQueryAgent V2 的简单 API"
    },
    "servers": [
        {"url": "https://jsonplaceholder.typicode.com"}
    ],
    "paths": {
        "/posts": {
            "get": {
                "operationId": "listPosts",
                "summary": "获取文章列表",
                "description": "获取所有文章列表，支持按用户ID过滤",
                "parameters": [
                    {
                        "name": "userId",
                        "in": "query",
                        "description": "用户ID",
                        "schema": {"type": "integer"},
                        "required": False
                    }
                ]
            }
        },
        "/posts/{id}": {
            "get": {
                "operationId": "getPost",
                "summary": "获取单篇文章",
                "description": "根据ID获取文章详情",
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "description": "文章ID",
                        "schema": {"type": "integer"},
                        "required": True
                    }
                ]
            }
        }
    }
}


def test_openapi_parser():
    """测试 OpenAPI 解析器"""
    print("=" * 60)
    print("测试 1: OpenAPI 解析器")
    print("=" * 60)

    # 创建临时文件
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(TEST_OPENAPI_SPEC, f)
        temp_file = f.name

    try:
        # 测试解析
        parser = OpenAPIParser(temp_file)

        print(f"✓ 解析成功")
        print(f"  - API 标题: {parser.title}")
        print(f"  - 版本: {parser.version}")
        print(f"  - 基础 URL: {parser.base_url}")

        # 获取端点
        endpoints = parser.get_endpoints()
        print(f"  - 端点数量: {len(endpoints)}")

        for ep in endpoints:
            print(f"    - {ep.method} {ep.path} ({ep.operation_id})")

        return True

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        os.unlink(temp_file)


def test_api_tool_manager():
    """测试 API Tool 管理器"""
    print("\n" + "=" * 60)
    print("测试 2: API Tool 管理器")
    print("=" * 60)

    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(TEST_OPENAPI_SPEC, f)
        temp_file = f.name

    try:
        parser = OpenAPIParser(temp_file)
        tool_manager = APIToolManager(parser)

        # 创建工具
        tools = tool_manager.create_tools()
        print(f"✓ 工具创建成功")
        print(f"  - 工具数量: {len(tools)}")

        for tool in tools:
            print(f"    - {tool.name}")
            print(f"      描述: {tool.description[:100]}...")

        return True

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        os.unlink(temp_file)


async def test_data_query_agent():
    """测试 DataQueryAgent"""
    print("\n" + "=" * 60)
    print("测试 3: DataQueryAgent")
    print("=" * 60)

    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(TEST_OPENAPI_SPEC, f)
        temp_file = f.name

    try:
        # 创建 Agent
        agent = DataQueryAgent(
            openapi_spec=temp_file,
            max_iterations=3
        )

        print(f"✓ Agent 创建成功")
        print(f"  - 可用工具: {agent.get_available_tools()}")

        # 获取工具详情
        for tool_name in agent.get_available_tools():
            details = agent.get_tool_details(tool_name)
            print(f"  - {details['name']}: {details['description'][:80]}...")

        return True

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        os.unlink(temp_file)


async def test_with_real_api():
    """使用真实 API 进行测试（需要 LLM 配置）"""
    print("\n" + "=" * 60)
    print("测试 4: 使用真实 API 测试（需要 LLM 配置）")
    print("=" * 60)

    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(TEST_OPENAPI_SPEC, f)
        temp_file = f.name

    try:
        # 创建 Agent
        agent = DataQueryAgent(
            openapi_spec=temp_file,
            max_iterations=2
        )

        print("执行查询: '获取 ID 为 1 的文章'")

        # 执行查询
        result = await agent.query(
            user_query="获取 ID 为 1 的文章"
        )

        print(f"✓ 查询完成")
        print(f"  - 决策: {result.agent_decision}")
        print(f"  - 理由: {result.reasoning}")
        print(f"  - 执行时间: {result.execution_time_ms}ms")
        print(f"  - 迭代次数: {len(result.iterations)}")

        if result.api_response:
            print(f"  - API 响应: {str(result.api_response)[:200]}...")

        if result.formatted_result:
            print(f"  - 格式化结果: {result.formatted_result[:200]}...")

        return True

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        os.unlink(temp_file)


def run_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("DataQueryAgent V2 测试套件")
    print("=" * 60)

    results = []

    # 测试 1: OpenAPI 解析器
    results.append(("OpenAPI 解析器", test_openapi_parser()))

    # 测试 2: API Tool 管理器
    results.append(("API Tool 管理器", test_api_tool_manager()))

    # 测试 3: DataQueryAgent（基础功能）
    results.append(("DataQueryAgent 基础", asyncio.run(test_data_query_agent())))

    # 测试 4: 使用真实 API（可选，需要 LLM 配置）
    # results.append(("DataQueryAgent 完整流程", asyncio.run(test_with_real_api())))

    # 打印总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {status}: {name}")

    print(f"\n总计: {passed}/{total} 通过")

    return passed == total


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
