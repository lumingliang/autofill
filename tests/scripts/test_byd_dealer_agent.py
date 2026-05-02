"""
测试比亚迪经销商门店 Agent 查询功能
使用 Query Agent 通过聊天记录查询门店信息
"""
import asyncio
import json
import os
from typing import Optional

import httpx
from dotenv import load_dotenv

from app.services.query_agent import QueryAgent

# 加载环境变量
load_dotenv()

# API 基础地址
BASE_URL = "http://localhost:8000"

# 测试用的聊天记录示例
CHAT_HISTORY_EXAMPLES = [
    {
        "name": "简单查询",
        "chat": """
客服：您好，请问有什么可以帮您？
客户：我想了解一下比亚迪的门店
客服：您所在的城市是哪里呢？
客户：我在北京朝阳区
        """,
        "expected_city": "北京",
        "expected_district": "朝阳区"
    },
    {
        "name": "错别字查询",
        "chat": """
客服：您好！
客户：我想去比压迪的4S店
客服：请问您在哪个城市？
客户：我在上海浦东
        """,
        "expected_city": "上海",
        "expected_district": "浦东"
    },
    {
        "name": "具体门店查询",
        "chat": """
客服：您好，比亚迪汽车服务中心！
客户：你好，我想问一下深圳福田区有没有比亚迪门店？
客服：有的，请问您是想看车还是做保养？
客户：我想去看车，了解一下新能源车
        """,
        "expected_city": "深圳",
        "expected_district": "福田区"
    },
    {
        "name": "模糊查询",
        "chat": """
客服：您好！
客户：我在广州天河这边，想找最近的比亚迪店
客服：您是需要购车还是售后服务？
客户：先看看车
        """,
        "expected_city": "广州",
        "expected_district": "天河"
    },
    {
        "name": "多城市提及",
        "chat": """
客服：您好，请问有什么可以帮您？
客户：我之前在北京的比亚迪店看过车，现在来上海工作了
客服：那您是想在上海看车吗？
客户：对的，我在上海徐汇区
        """,
        "expected_city": "上海",
        "expected_district": "徐汇区"
    }
]


def get_api_key() -> str:
    """获取 API Key"""
    # 尝试从环境变量获取
    api_key = os.getenv("BYD_DEALER_API_KEY")
    if api_key:
        return api_key

    # 默认使用测试 API Key
    return "test_api_key"


async def test_public_api_direct():
    """直接测试公开 API"""
    print("\n" + "=" * 60)
    print("测试公开 API 直接调用")
    print("=" * 60)

    api_key = get_api_key()

    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # 测试1: 简单查询
        print("\n1. 测试简单查询...")
        response = await client.post(
            "/byd-dealers/search",
            json={
                "app_key": api_key,
                "query": "查找北京朝阳区的比亚迪4S店",
                "limit": 5
            }
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✓ 查询成功")
            print(f"  - 找到 {result.get('total', 0)} 家门店")
            print(f"  - 匹配关键词: {result.get('matched_keywords', [])}")

            if result.get('data'):
                for i, dealer in enumerate(result['data'][:3], 1):
                    print(f"  {i}. {dealer['name']} ({dealer['city']}{dealer.get('district', '')})")
        else:
            print(f"✗ 查询失败: {response.status_code}")
            print(f"  响应: {response.text}")

        # 测试2: 聊天记录查询
        print("\n2. 测试聊天记录查询...")
        chat_history = """
客服：您好，请问有什么可以帮您？
客户：我想了解一下比亚迪的门店
客服：您所在的城市是哪里呢？
客户：我在深圳南山区
        """

        response = await client.post(
            "/byd-dealers/chat-search",
            json={
                "app_key": api_key,
                "chat_history": chat_history,
                "limit": 5
            }
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✓ 查询成功")
            print(f"  - 找到 {result.get('total', 0)} 家门店")
            print(f"  - 匹配关键词: {result.get('matched_keywords', [])}")

            if result.get('data'):
                for i, dealer in enumerate(result['data'][:3], 1):
                    print(f"  {i}. {dealer['name']} ({dealer['city']}{dealer.get('district', '')})")
        else:
            print(f"✗ 查询失败: {response.status_code}")
            print(f"  响应: {response.text}")


async def test_with_query_agent():
    """使用 Query Agent 测试"""
    print("\n" + "=" * 60)
    print("使用 Query Agent 测试")
    print("=" * 60)

    api_key = get_api_key()

    # 创建 Agent（使用 mock LLM 避免需要真实 API key）
    from unittest.mock import MagicMock

    mock_llm = MagicMock()
    mock_llm.model_name = "gpt-4o"
    mock_llm.temperature = 0.0

    # 模拟 LLM 响应
    def mock_invoke(messages):
        # 从消息中提取查询内容
        content = messages[0][1] if messages else ""

        # 模拟参数提取
        params = {"keyword": "比亚迪"}

        if "北京" in content:
            params["city"] = "北京"
        elif "上海" in content:
            params["city"] = "上海"
        elif "深圳" in content:
            params["city"] = "深圳"
        elif "广州" in content:
            params["city"] = "广州"

        if "朝阳" in content:
            params["district"] = "朝阳区"
        elif "浦东" in content:
            params["district"] = "浦东新区"
        elif "福田" in content:
            params["district"] = "福田区"
        elif "南山" in content:
            params["district"] = "南山区"

        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "parameters": params,
            "reasoning": f"从查询中提取到城市: {params.get('city', '未知')}, 区域: {params.get('district', '未知')}"
        })
        return mock_response

    mock_llm.invoke = mock_invoke

    agent = QueryAgent(llm=mock_llm)

    # 构建 curl 模板
    curl_template = f"""
    curl -X POST '{BASE_URL}/byd-dealers/search' \
    -H 'Content-Type: application/json' \
    -d '{{
        "app_key": "{api_key}",
        "query": "{{{{keyword}}}}",
        "city": "{{{{city}}}}",
        "limit": 10
    }}'
    """

    # 测试每个聊天记录
    for i, example in enumerate(CHAT_HISTORY_EXAMPLES, 1):
        print(f"\n{i}. 测试场景: {example['name']}")
        print(f"   聊天记录:\n{example['chat']}")

        try:
            # 使用 mock 工作流结果
            mock_result = {
                "is_satisfied": True,
                "final_result": {
                    "name": f"比亚迪{example['expected_city']}4S店",
                    "city": example['expected_city'],
                    "district": example['expected_district'],
                    "address": f"{example['expected_city']}{example['expected_district']}测试路1号"
                },
                "final_raw_response": {
                    "success": True,
                    "data": [
                        {
                            "name": f"比亚迪{example['expected_city']}4S店",
                            "city": example['expected_city'],
                            "district": example['expected_district']
                        }
                    ]
                },
                "final_reasoning": f"找到{example['expected_city']}的门店",
                "attempt_count": 1,
                "search_history": [],
                "current_parameters": {
                    "keyword": "比亚迪",
                    "city": example['expected_city'],
                    "district": example['expected_district']
                }
            }

            agent.workflow = MagicMock()
            agent.workflow.invoke.return_value = mock_result

            result = agent.run(
                query=example['chat'],
                curl=curl_template,
                system_prompt="""
                查询目标是找到符合用户需求的比亚迪经销商门店。

                匹配标准：
                1. 从聊天记录中提取客户提到的城市和区域
                2. 匹配该城市和区域的比亚迪门店
                3. 优先返回最匹配的一条记录

                注意：客户可能在聊天记录中提到多个城市，以最后一个提到的为准。
                """,
                max_attempts=3,
                timeout=30
            )

            if result.success:
                print(f"   ✓ 查询成功")
                print(f"     - 预期城市: {example['expected_city']}")
                print(f"     - 预期区域: {example['expected_district']}")
                print(f"     - 找到结果: {result.data}")
            else:
                print(f"   ✗ 查询失败: {result.reasoning}")

        except Exception as e:
            print(f"   ✗ 测试异常: {e}")


def test_curl_parsing():
    """测试 curl 解析"""
    print("\n" + "=" * 60)
    print("测试 Curl 解析")
    print("=" * 60)

    from app.services.query_agent import CurlParser

    curl = f"""
    curl -X POST '{BASE_URL}/byd-dealers/search' \
    -H 'Content-Type: application/json' \
    -d '{{
        "app_key": "test_key",
        "query": "{{{{keyword}}}}",
        "city": "{{{{city}}}}",
        "limit": 10
    }}'
    """

    try:
        result = CurlParser.parse(curl)
        print(f"✓ Curl 解析成功")
        print(f"  - URL: {result.url}")
        print(f"  - Method: {result.method}")
        print(f"  - Headers: {result.headers}")
        print(f"  - Body Template: {result.body_template}")
        print(f"  - Placeholder Fields: {result.placeholder_fields}")
    except Exception as e:
        print(f"✗ Curl 解析失败: {e}")


async def main():
    """主函数"""
    print("=" * 60)
    print("比亚迪经销商门店 Agent 测试")
    print("=" * 60)

    # 测试 curl 解析
    test_curl_parsing()

    # 测试公开 API
    try:
        await test_public_api_direct()
    except Exception as e:
        print(f"\n公开 API 测试失败（可能是服务未启动）: {e}")

    # 使用 Query Agent 测试
    try:
        await test_with_query_agent()
    except Exception as e:
        print(f"\nQuery Agent 测试失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
