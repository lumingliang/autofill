"""
测试 API Tool 实际调用功能
"""
import asyncio
import json
import tempfile
import os

from app.services.agent_v2 import OpenAPIParser, APIToolManager


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
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                ]
            }
        },
        "/posts": {
            "get": {
                "operationId": "listPosts",
                "summary": "获取文章列表",
                "parameters": [
                    {"name": "userId", "in": "query", "required": False, "schema": {"type": "integer"}}
                ]
            }
        }
    }
}


async def test_tool_invoke():
    print("=" * 60)
    print("测试 API Tool 调用")
    print("=" * 60)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(TEST_SPEC, f)
        temp_file = f.name

    try:
        parser = OpenAPIParser(temp_file)
        tool_manager = APIToolManager(parser)
        tools = tool_manager.create_tools()

        print(f"工具数量: {len(tools)}")

        # 测试 1: 调用 getPost 工具
        print("\n" + "-" * 40)
        print("测试 1: 调用 getPost 工具")
        print("-" * 40)

        get_post_tool = None
        for tool in tools:
            if tool.name == "getPost":
                get_post_tool = tool
                break

        if get_post_tool:
            print(f"调用工具: {get_post_tool.name}")
            print(f"参数: {{'id': 1}}")

            result = await get_post_tool.ainvoke({"id": 1})

            # 解析结果
            try:
                data = json.loads(result)
                print(f"\n✓ 调用成功")
                print(f"  文章ID: {data.get('id', 'N/A')}")
                print(f"  标题: {data.get('title', 'N/A')[:50]}...")
                print(f"  用户ID: {data.get('userId', 'N/A')}")
            except Exception as e:
                print(f"\n✗ 解析失败: {e}")
                print(f"  响应: {result[:100]}...")
        else:
            print("✗ 未找到 getPost 工具")

        # 测试 2: 调用 listPosts 工具
        print("\n" + "-" * 40)
        print("测试 2: 调用 listPosts 工具")
        print("-" * 40)

        list_posts_tool = None
        for tool in tools:
            if tool.name == "listPosts":
                list_posts_tool = tool
                break

        if list_posts_tool:
            print(f"调用工具: {list_posts_tool.name}")
            print(f"参数: {{'userId': 1}}")

            result = await list_posts_tool.ainvoke({"userId": 1})

            # 解析结果
            try:
                data = json.loads(result)
                print(f"\n✓ 调用成功")
                print(f"  返回数量: {len(data)} 条")
                if len(data) > 0:
                    print(f"  第一条标题: {data[0].get('title', 'N/A')[:50]}...")
            except Exception as e:
                print(f"\n✗ 解析失败: {e}")
                print(f"  响应: {result[:100]}...")
        else:
            print("✗ 未找到 listPosts 工具")

        # 测试 3: 无参数调用
        print("\n" + "-" * 40)
        print("测试 3: 无参数调用 listPosts")
        print("-" * 40)

        if list_posts_tool:
            print(f"调用工具: {list_posts_tool.name}")
            print(f"参数: {{}}")

            result = await list_posts_tool.ainvoke({})

            try:
                data = json.loads(result)
                print(f"\n✓ 调用成功")
                print(f"  返回数量: {len(data)} 条")
            except Exception as e:
                print(f"\n✗ 解析失败: {e}")
                print(f"  响应: {result[:100]}...")

    finally:
        os.unlink(temp_file)


if __name__ == "__main__":
    asyncio.run(test_tool_invoke())
