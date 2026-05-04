"""
DataQueryAgent V2 集成测试

需要启动应用服务后才能运行此测试。
"""
import asyncio
import json
import httpx


async def test_api_endpoints():
    """测试 API 端点"""
    print("=" * 60)
    print("测试 DataQueryAgent V2 API 端点")
    print("=" * 60)

    base_url = "http://localhost:8000"

    # 测试用的 OpenAPI 规范
    test_spec = {
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
            }
        }
    }

    async with httpx.AsyncClient() as client:
        # 测试 1: 获取工具列表
        print("\n" + "-" * 40)
        print("测试 1: 获取工具列表 (POST /api/v2/agent/tools)")
        print("-" * 40)

        try:
            response = await client.post(
                f"{base_url}/api/v2/agent/tools",
                json={
                    "query": "test",
                    "openapi_spec": json.dumps(test_spec)
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✓ 请求成功")
                print(f"  工具数量: {data.get('total', 0)}")
                for tool in data.get('tools', []):
                    print(f"  - {tool['name']}")
            else:
                print(f"✗ 请求失败: {response.status_code}")
                print(f"  响应: {response.text[:200]}")

        except Exception as e:
            print(f"✗ 请求异常: {e}")

        # 测试 2: 执行查询（简化版接口，无需认证）
        print("\n" + "-" * 40)
        print("测试 2: 执行查询 (POST /api/v2/agent/query/simple)")
        print("-" * 40)

        try:
            response = await client.post(
                f"{base_url}/api/v2/agent/query/simple",
                json={
                    "query": "获取 ID 为 1 的文章",
                    "openapi_spec": json.dumps(test_spec),
                    "max_iterations": 2
                },
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✓ 请求成功")
                print(f"  决策: {data.get('agent_decision')}")
                print(f"  理由: {data.get('reasoning', 'N/A')[:100]}...")
                print(f"  执行时间: {data.get('execution_time_ms')}ms")
                print(f"  迭代次数: {len(data.get('iterations', []))}")

                if data.get('formatted_result'):
                    print(f"  格式化结果: {data['formatted_result'][:100]}...")
            else:
                print(f"✗ 请求失败: {response.status_code}")
                print(f"  响应: {response.text[:200]}")

        except Exception as e:
            print(f"✗ 请求异常: {e}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_api_endpoints())
