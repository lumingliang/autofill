"""
比亚迪经销商门店 Agent 查询演示
展示如何使用 Query Agent 通过聊天记录查询门店信息
"""
import asyncio
import json
from typing import Dict, Any, List

from app.services.query_agent import QueryAgent, CurlParser


# 模拟聊天记录示例
CHAT_HISTORY_SAMPLES = [
    {
        "name": "北京朝阳区查询",
        "chat": """
客服：您好，请问有什么可以帮您？
客户：我想了解一下比亚迪的门店
客服：您所在的城市是哪里呢？
客户：我在北京朝阳区
        """,
        "expected": {
            "city": "北京",
            "district": "朝阳区"
        }
    },
    {
        "name": "深圳南山查询（有错别字）",
        "chat": """
客服：您好！
客户：我想去比压迪的4S店
客服：请问您在哪个城市？
客户：我在深圳南山区
        """,
        "expected": {
            "city": "深圳",
            "district": "南山区"
        }
    },
    {
        "name": "上海浦东查询",
        "chat": """
客服：您好，比亚迪汽车服务中心！
客户：你好，我想问一下上海浦东有没有比亚迪门店？
客服：有的，请问您是想看车还是做保养？
客户：我想去看车，了解一下新能源车
        """,
        "expected": {
            "city": "上海",
            "district": "浦东新区"
        }
    },
    {
        "name": "广州天河查询",
        "chat": """
客服：您好！
客户：我在广州天河这边，想找最近的比亚迪店
客服：您是需要购车还是售后服务？
客户：先看看车
        """,
        "expected": {
            "city": "广州",
            "district": "天河区"
        }
    },
    {
        "name": "多城市提及（以上海为准）",
        "chat": """
客服：您好，请问有什么可以帮您？
客户：我之前在北京的比亚迪店看过车，现在来上海工作了
客服：那您是想在上海看车吗？
客户：对的，我在上海徐汇区
        """,
        "expected": {
            "city": "上海",
            "district": "徐汇区"
        }
    }
]


def create_mock_llm():
    """创建模拟 LLM 用于测试"""
    from unittest.mock import MagicMock

    mock_llm = MagicMock()
    mock_llm.model_name = "gpt-4o"
    mock_llm.temperature = 0.0

    def mock_invoke(messages):
        """模拟 LLM 调用，从消息中提取城市和区域"""
        content = messages[0][1] if messages else ""

        # 提取城市和区域
        params = {"keyword": "比亚迪"}

        # 城市映射
        city_keywords = {
            "北京": "北京",
            "上海": "上海",
            "深圳": "深圳",
            "广州": "广州",
            "成都": "成都",
            "杭州": "杭州",
            "武汉": "武汉",
            "西安": "西安",
            "重庆": "重庆",
            "南京": "南京"
        }

        # 区域映射
        district_keywords = {
            "朝阳": "朝阳区",
            "海淀": "海淀区",
            "浦东": "浦东新区",
            "南山": "南山区",
            "福田": "福田区",
            "天河": "天河区",
            "徐汇": "徐汇区",
            "静安": "静安区"
        }

        # 提取城市
        for keyword, city in city_keywords.items():
            if keyword in content:
                params["city"] = city

        # 提取区域
        for keyword, district in district_keywords.items():
            if keyword in content:
                params["district"] = district

        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "parameters": params,
            "reasoning": f"从聊天记录中提取到城市: {params.get('city', '未知')}, 区域: {params.get('district', '未知')}"
        })
        return mock_response

    mock_llm.invoke = mock_invoke
    return mock_llm


def create_mock_workflow():
    """创建模拟工作流"""
    from unittest.mock import MagicMock

    def mock_invoke(state):
        """模拟工作流调用"""
        query = state.get("query", "")
        parameters = state.get("current_parameters", {})

        # 模拟搜索结果
        city = parameters.get("city", "未知")
        district = parameters.get("district", "")

        mock_result = {
            "is_satisfied": True,
            "final_result": {
                "name": f"比亚迪{city}{district}4S店" if district else f"比亚迪{city}4S店",
                "city": city,
                "district": district or "市中心",
                "address": f"{city}{district or ''}测试路1号",
                "phone": "400-888-8888"
            },
            "final_raw_response": {
                "success": True,
                "data": [
                    {
                        "name": f"比亚迪{city}{district}4S店" if district else f"比亚迪{city}4S店",
                        "city": city,
                        "district": district or "市中心",
                        "address": f"{city}{district or ''}测试路1号",
                        "phone": "400-888-8888"
                    }
                ],
                "total": 1
            },
            "final_reasoning": f"成功找到{city}的比亚迪门店",
            "attempt_count": 1,
            "search_history": [
                {
                    "attempt_number": 1,
                    "parameters": parameters,
                    "result_count": 1,
                    "selected_indices": [0],
                    "reasoning": f"找到{city}的门店",
                    "raw_response": {"success": True, "total": 1}
                }
            ],
            "current_parameters": parameters
        }

        return mock_result

    mock_workflow = MagicMock()
    mock_workflow.invoke = mock_invoke
    return mock_workflow


def test_curl_parsing():
    """测试 curl 解析功能"""
    print("\n" + "=" * 70)
    print("测试 Curl 解析功能")
    print("=" * 70)

    curl_command = """
    curl -X POST 'http://localhost:8000/byd-dealers/search' \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer test_token' \
    -d '{
        "app_key": "{{app_key}}",
        "query": "{{keyword}}",
        "city": "{{city}}",
        "district": "{{district}}",
        "limit": 10
    }'
    """

    try:
        result = CurlParser.parse(curl_command)

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


def test_placeholder_replacement():
    """测试占位符替换功能"""
    print("\n" + "=" * 70)
    print("测试占位符替换功能")
    print("=" * 70)

    from app.services.query_agent.utils import replace_placeholders

    template = {
        "app_key": "{{app_key}}",
        "query": "{{keyword}}",
        "city": "{{city}}",
        "district": "{{district}}",
        "limit": 10
    }

    parameters = {
        "app_key": "test_api_key_123",
        "keyword": "比亚迪4S店",
        "city": "北京",
        "district": "朝阳区"
    }

    try:
        result = replace_placeholders(template, parameters)

        print("\n✓ 占位符替换成功")
        print(f"  模板: {json.dumps(template, ensure_ascii=False)}")
        print(f"  参数: {json.dumps(parameters, ensure_ascii=False)}")
        print(f"  结果: {json.dumps(result, ensure_ascii=False)}")

        return True
    except Exception as e:
        print(f"\n✗ 占位符替换失败: {e}")
        return False


def test_query_agent():
    """测试 Query Agent"""
    print("\n" + "=" * 70)
    print("测试 Query Agent")
    print("=" * 70)

    # 创建模拟 LLM 和工作流
    mock_llm = create_mock_llm()
    mock_workflow = create_mock_workflow()

    # 创建 Agent
    agent = QueryAgent(llm=mock_llm)
    agent.workflow = mock_workflow

    # 测试 curl 命令
    curl_command = """
    curl -X POST 'http://localhost:8000/byd-dealers/search' \
    -H 'Content-Type: application/json' \
    -d '{
        "app_key": "test_api_key",
        "query": "{{keyword}}",
        "city": "{{city}}",
        "district": "{{district}}",
        "limit": 5
    }'
    """

    # 测试每个聊天记录
    success_count = 0
    for i, sample in enumerate(CHAT_HISTORY_SAMPLES, 1):
        print(f"\n{i}. 测试场景: {sample['name']}")
        print(f"   聊天记录:\n{sample['chat']}")

        try:
            result = agent.run(
                query=sample['chat'],
                curl=curl_command,
                system_prompt="""
                查询目标是找到符合用户需求的比亚迪经销商门店。

                匹配标准：
                1. 从聊天记录中提取客户提到的城市和区域
                2. 匹配该城市和区域的比亚迪门店
                3. 优先返回最匹配的一条记录

                注意：客户可能在聊天记录中提到多个城市，以最后一个提到的为准。
                支持处理错别字，如"比压迪"应该识别为"比亚迪"。
                """,
                max_attempts=3,
                timeout=30
            )

            if result.success:
                print(f"   ✓ 查询成功")
                print(f"     - 预期城市: {sample['expected']['city']}")
                print(f"     - 预期区域: {sample['expected']['district']}")
                print(f"     - 找到结果: {result.data}")
                success_count += 1
            else:
                print(f"   ✗ 查询失败: {result.reasoning}")

        except Exception as e:
            print(f"   ✗ 测试异常: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n测试完成: {success_count}/{len(CHAT_HISTORY_SAMPLES)} 个场景通过")
    return success_count == len(CHAT_HISTORY_SAMPLES)


def test_result_selection():
    """测试结果选择功能"""
    print("\n" + "=" * 70)
    print("测试结果选择功能")
    print("=" * 70)

    from app.services.query_agent.utils import select_results

    # 模拟 API 响应
    api_response = {
        "success": True,
        "data": {
            "items": [
                {"id": 1, "name": "比亚迪北京朝阳4S店", "city": "北京", "district": "朝阳区"},
                {"id": 2, "name": "比亚迪北京海淀4S店", "city": "北京", "district": "海淀区"},
                {"id": 3, "name": "比亚迪北京丰台4S店", "city": "北京", "district": "丰台区"}
            ],
            "total": 3
        },
        "message": "查询成功"
    }

    # 测试不同的选择器
    selectors = [
        ("data.items[0]", "选择第一个门店"),
        ("data.items[*].name", "选择所有门店名称"),
        ("data.total", "选择总数"),
        (None, "返回完整响应")
    ]

    for selector, description in selectors:
        try:
            result = select_results(api_response, selector)
            print(f"\n✓ {description}")
            print(f"  选择器: {selector}")
            print(f"  结果: {json.dumps(result, ensure_ascii=False)}")
        except Exception as e:
            print(f"\n✗ {description} 失败: {e}")

    return True


def main():
    """主函数"""
    print("=" * 70)
    print("比亚迪经销商门店 Agent 查询演示")
    print("=" * 70)
    print("\n本演示展示如何使用 Query Agent 通过聊天记录查询比亚迪门店信息")
    print("包括以下功能测试：")
    print("  1. Curl 解析")
    print("  2. 占位符替换")
    print("  3. Query Agent 完整流程")
    print("  4. 结果选择")

    # 运行测试
    results = []

    results.append(("Curl 解析", test_curl_parsing()))
    results.append(("占位符替换", test_placeholder_replacement()))
    results.append(("Query Agent", test_query_agent()))
    results.append(("结果选择", test_result_selection()))

    # 打印总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)

    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")

    all_passed = all(passed for _, passed in results)
    print("\n" + "=" * 70)
    if all_passed:
        print("所有测试通过！")
    else:
        print("部分测试失败，请检查实现")
    print("=" * 70)


if __name__ == "__main__":
    main()
