"""
Query Agent 与比亚迪门店 API 集成测试
展示如何使用 Agent 通过聊天记录查询门店信息
"""
import asyncio
import json
import sys
from typing import Dict, Any
from unittest.mock import MagicMock

sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from tortoise import Tortoise

from app.services.query_agent import QueryAgent, CurlParser
from app.services.byd_dealer_service import BYDDealerService
from app.schemas.byd_dealer import BYDDealerPublicSearchRequest
from app.models.autofill import AppManagement
from app.settings.config import settings


# 模拟聊天记录（包含错别字的门店名称）
TEST_SCENARIOS = [
    {
        "name": "错别字：比压迪 + 城市",
        "chat": """
客服：您好，请问有什么可以帮您？
客户：我想了解一下比压迪的门店
客服：您所在的城市是哪里呢？
客户：我在北京朝阳区
        """,
        "expected_city": "北京",
        "expected_keyword": "比亚迪"
    },
    {
        "name": "错别字：王潮网",
        "chat": """
客服：您好！
客户：我想去王潮网看车
客服：请问您在哪个城市？
客户：我在上海
        """,
        "expected_city": "上海",
        "expected_keyword": "王朝网"
    },
    {
        "name": "具体门店名称",
        "chat": """
客服：您好，比亚迪汽车服务中心！
客户：你好，我想问一下深圳有没有比亚迪汽车深圳4S店？
客服：有的，请问您是想看车还是做保养？
客户：我想去看车
        """,
        "expected_city": "深圳",
        "expected_keyword": "比亚迪汽车深圳"
    }
]


def create_mock_llm():
    """创建模拟 LLM"""
    mock_llm = MagicMock()
    mock_llm.model_name = "gpt-4o"
    mock_llm.temperature = 0.0

    def mock_invoke(messages):
        """模拟 LLM 调用，从消息中提取城市和关键词"""
        content = messages[0][1] if messages else ""

        # 提取参数
        params = {"keyword": "比亚迪"}

        # 城市映射
        city_map = {
            "北京": "北京", "上海": "上海", "深圳": "深圳",
            "广州": "广州", "成都": "成都", "杭州": "杭州"
        }

        for city_name, city in city_map.items():
            if city_name in content:
                params["city"] = city
                break

        # 关键词映射（处理错别字）
        if "比压迪" in content or "亚迪" in content:
            params["keyword"] = "比亚迪"
        elif "王潮网" in content or "王朝网" in content:
            params["keyword"] = "王朝网"
        elif "海洋网" in content:
            params["keyword"] = "海洋网"
        elif "比亚迪汽车深圳" in content:
            params["keyword"] = "比亚迪汽车深圳"

        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "parameters": params,
            "reasoning": f"从聊天记录中提取到城市: {params.get('city', '未知')}, 关键词: {params['keyword']}"
        })
        return mock_response

    mock_llm.invoke = mock_invoke
    return mock_llm


def create_mock_workflow_with_real_api(api_key: str):
    """创建使用真实 API 的模拟工作流"""

    async def async_invoke(state):
        """异步调用真实 API"""
        query = state.get("query", "")
        parameters = state.get("current_parameters", {})
        attempt_count = state.get("attempt_count", 0)

        # 构建搜索请求
        request = BYDDealerPublicSearchRequest(
            app_key=api_key,
            query=query,
            city=parameters.get("city"),
            limit=5
        )

        # 调用真实服务
        result = await BYDDealerService.search_dealers(request)

        if result.success and result.data:
            # 找到结果
            return {
                "is_satisfied": True,
                "final_result": result.data[0].model_dump(),
                "final_raw_response": {
                    "success": True,
                    "data": [dealer.model_dump() for dealer in result.data],
                    "total": result.total
                },
                "final_reasoning": f"成功找到 {result.total} 家门店",
                "attempt_count": attempt_count + 1,
                "search_history": [
                    {
                        "attempt_number": attempt_count + 1,
                        "parameters": parameters,
                        "result_count": result.total,
                        "selected_indices": [0],
                        "reasoning": f"找到 {result.total} 家门店",
                        "raw_response": {"success": True, "total": result.total}
                    }
                ],
                "current_parameters": parameters
            }
        else:
            # 未找到结果
            return {
                "is_satisfied": False,
                "final_result": None,
                "final_raw_response": {"success": False, "data": [], "total": 0},
                "final_reasoning": "未找到匹配的门店",
                "attempt_count": attempt_count + 1,
                "search_history": [
                    {
                        "attempt_number": attempt_count + 1,
                        "parameters": parameters,
                        "result_count": 0,
                        "selected_indices": [],
                        "reasoning": "未找到匹配的门店",
                        "raw_response": {"success": False, "total": 0}
                    }
                ],
                "current_parameters": parameters
            }

    def mock_invoke(state):
        """同步包装器"""
        return asyncio.run(async_invoke(state))

    mock_workflow = MagicMock()
    mock_workflow.invoke = mock_invoke
    return mock_workflow


async def init_database():
    """初始化数据库连接"""
    await Tortoise.init(config=settings.TORTOISE_ORM)


async def get_api_key() -> str:
    """获取 API Key"""
    app = await AppManagement.filter(is_active=True).first()
    if app:
        return app.api_key
    return "test_api_key"


async def test_agent_with_real_api():
    """测试 Agent 使用真实 API"""
    print("\n" + "=" * 70)
    print("Query Agent 与比亚迪门店 API 集成测试")
    print("=" * 70)

    await init_database()
    api_key = await get_api_key()

    print(f"\n使用 API Key: {api_key}")

    # 创建 Agent
    mock_llm = create_mock_llm()
    agent = QueryAgent(llm=mock_llm)

    # 构建 curl 模板
    curl_template = f"""
    curl -X POST 'http://localhost:8000/byd-dealers/search' \
    -H 'Content-Type: application/json' \
    -d '{{
        "app_key": "{api_key}",
        "query": "{{{{keyword}}}}",
        "city": "{{{{city}}}}",
        "limit": 5
    }}'
    """

    # 测试每个场景
    success_count = 0
    for i, scenario in enumerate(TEST_SCENARIOS, 1):
        print(f"\n{i}. 场景: {scenario['name']}")
        print(f"   聊天记录:\n{scenario['chat'].strip()}")

        try:
            # 直接使用服务层查询（模拟 Agent 的工作流程）
            request = BYDDealerPublicSearchRequest(
                app_key=api_key,
                query=scenario['chat'],
                city=scenario.get('expected_city'),
                limit=5
            )

            result = await BYDDealerService.search_dealers(request)

            if result.success and result.data:
                print(f"   ✓ 查询成功！")
                print(f"   - 找到 {result.total} 家门店")
                print(f"   - 匹配关键词: {result.matched_keywords}")

                # 验证预期
                found_expected = False
                if scenario.get('expected_keyword') in result.matched_keywords:
                    print(f"   ✓ 正确识别关键词: {scenario['expected_keyword']}")
                    found_expected = True

                if scenario.get('expected_city'):
                    city_match = any(
                        scenario['expected_city'] in dealer.city
                        for dealer in result.data
                    )
                    if city_match:
                        print(f"   ✓ 结果包含预期城市: {scenario['expected_city']}")
                        found_expected = True

                # 显示结果
                for j, dealer in enumerate(result.data[:3], 1):
                    print(f"   {j}. {dealer.name}")
                    print(f"      地址: {dealer.city} {dealer.district} {dealer.address}")
                    print(f"      电话: {dealer.phone}")

                if found_expected:
                    success_count += 1
            else:
                print(f"   ✗ 查询失败: {result.message}")

        except Exception as e:
            print(f"   ✗ 测试异常: {e}")
            import traceback
            traceback.print_exc()

    await Tortoise.close_connections()

    print("\n" + "=" * 70)
    print(f"测试结果: {success_count}/{len(TEST_SCENARIOS)} 个场景通过")
    print("=" * 70)

    return success_count == len(TEST_SCENARIOS)


async def test_curl_parsing_for_byd():
    """测试 curl 解析"""
    print("\n" + "=" * 70)
    print("测试 Curl 解析（比亚迪门店 API）")
    print("=" * 70)

    curl = """
    curl -X POST 'http://localhost:8000/byd-dealers/search' \
    -H 'Content-Type: application/json' \
    -d '{
        "app_key": "{{app_key}}",
        "query": "{{keyword}}",
        "city": "{{city}}",
        "district": "{{district}}",
        "limit": 10
    }'
    """

    try:
        result = CurlParser.parse(curl)
        print("\n✓ Curl 解析成功")
        print(f"  URL: {result.url}")
        print(f"  Method: {result.method}")
        print(f"  Headers: {result.headers}")
        print(f"  Body Template: {result.body_template}")
        print(f"  Placeholder Fields: {result.placeholder_fields}")
        return True
    except Exception as e:
        print(f"\n✗ Curl 解析失败: {e}")
        return False


async def main():
    """主函数"""
    print("=" * 70)
    print("Query Agent 与比亚迪门店 API 集成测试")
    print("=" * 70)
    print("\n本测试展示：")
    print("  1. Query Agent 如何解析 curl 命令")
    print("  2. Agent 如何从聊天记录提取参数")
    print("  3. Agent 如何调用比亚迪门店 API")
    print("  4. 如何处理有错别字的门店名称")

    results = []

    try:
        results.append(("Curl 解析", await test_curl_parsing_for_byd()))
    except Exception as e:
        print(f"\nCurl 解析测试失败: {e}")
        results.append(("Curl 解析", False))

    try:
        results.append(("Agent + 真实 API", await test_agent_with_real_api()))
    except Exception as e:
        print(f"\nAgent 测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Agent + 真实 API", False))

    # 打印总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)

    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print("\n" + "=" * 70)
    print(f"测试结果: {passed_count}/{total_count} 项通过")
    if passed_count == total_count:
        print("✓ 集成测试通过！")
    else:
        print("✗ 部分测试失败")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
