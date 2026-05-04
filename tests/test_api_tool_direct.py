"""
直接测试 API Tool 功能
"""
import asyncio
import json
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.services.agent_v2.openapi_parser import OpenAPIParser
from app.services.agent_v2.api_tool import APIToolManager


async def test_api_tool():
    """测试 API Tool 调用"""
    print("=" * 60)
    print("测试 API Tool 直接调用")
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

    print("\n1. 解析 OpenAPI 规范...")
    parser = OpenAPIParser(spec_str)
    print(f"   ✓ 解析到 {len(parser.get_endpoints())} 个端点")

    print("\n2. 创建 API Tool Manager...")
    tool_manager = APIToolManager(parser=parser)
    print("   ✓ Tool Manager 创建成功")

    print("\n3. 创建 Tools...")
    tools = tool_manager.create_tools()
    print(f"   ✓ 创建了 {len(tools)} 个工具")

    for tool in tools:
        print(f"   - {tool.name}: {tool.description[:50]}...")

    if tools:
        print("\n4. 测试工具调用...")
        tool = tools[0]
        print(f"   调用工具: {tool.name}")
        print(f"   参数: {{'id': 1}}")

        try:
            result = await tool.ainvoke({'id': 1})
            print(f"   ✓ 调用成功!")
            print(f"   结果: {result[:200]}...")

            # 解析结果
            data = json.loads(result)
            print(f"\n   解析后的数据:")
            print(f"   - ID: {data.get('id')}")
            print(f"   - Title: {data.get('title')}")
            print(f"   - User ID: {data.get('userId')}")

            return True

        except Exception as e:
            print(f"   ✗ 调用失败: {e}")
            return False

    return False


if __name__ == "__main__":
    success = asyncio.run(test_api_tool())
    print("\n" + "=" * 60)
    if success:
        print("✓ 所有测试通过!")
    else:
        print("✗ 测试失败")
    print("=" * 60)
