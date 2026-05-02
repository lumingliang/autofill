"""
Query Agent 简单测试
"""
from unittest.mock import MagicMock, patch

from app.services.query_agent import QueryAgent, CurlParser
from app.services.query_agent.utils import replace_placeholders, extract_by_selector


def test_curl_parser():
    """测试 Curl 解析"""
    print("=" * 50)
    print("测试 Curl 解析")
    print("=" * 50)

    curl = """
    curl -X POST 'https://api.example.com/search' \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer token123' \
    -d '{
        "keyword": "{{keyword}}",
        "city": "{{city}}"
    }'
    """

    result = CurlParser.parse(curl)
    print(f"URL: {result.url}")
    print(f"Method: {result.method}")
    print(f"Headers: {result.headers}")
    print(f"Body Template: {result.body_template}")
    print(f"Placeholder Fields: {result.placeholder_fields}")
    print("✓ Curl 解析测试通过\n")


def test_replace_placeholders():
    """测试占位符替换"""
    print("=" * 50)
    print("测试占位符替换")
    print("=" * 50)

    template = {
        "keyword": "{{keyword}}",
        "city": "{{city}}",
        "nested": {
            "name": "{{name}}"
        }
    }
    params = {
        "keyword": "星巴克",
        "city": "深圳",
        "name": "test"
    }

    result = replace_placeholders(template, params)
    print(f"输入: {template}")
    print(f"参数: {params}")
    print(f"输出: {result}")
    assert result["keyword"] == "星巴克"
    assert result["city"] == "深圳"
    assert result["nested"]["name"] == "test"
    print("✓ 占位符替换测试通过\n")


def test_extract_by_selector():
    """测试选择器提取"""
    print("=" * 50)
    print("测试选择器提取")
    print("=" * 50)

    data = {
        "code": 0,
        "message": "success",
        "data": {
            "items": [
                {"id": 1, "name": "item1"},
                {"id": 2, "name": "item2"}
            ],
            "total": 2
        }
    }

    # 测试点号路径
    result = extract_by_selector(data, "data.items")
    print(f"选择器: data.items")
    print(f"结果: {result}")
    assert len(result) == 2
    assert result[0]["name"] == "item1"
    print("✓ 点号路径选择器测试通过")

    # 测试数组索引
    result = extract_by_selector(data, "data.items.0")
    print(f"选择器: data.items.0")
    print(f"结果: {result}")
    assert result["name"] == "item1"
    print("✓ 数组索引选择器测试通过")

    # 测试 JSONPath
    result = extract_by_selector(data, "$.data.items[0]")
    print(f"选择器: $.data.items[0]")
    print(f"结果: {result}")
    assert result["name"] == "item1"
    print("✓ JSONPath 选择器测试通过\n")


def test_agent_initialization():
    """测试 Agent 初始化（使用 mock）"""
    print("=" * 50)
    print("测试 Agent 初始化")
    print("=" * 50)

    # 使用 mock 来避免需要真实的 API key
    mock_llm = MagicMock()
    mock_llm.model_name = "gpt-4o"
    mock_llm.temperature = 0.0

    agent = QueryAgent(llm=mock_llm)
    print(f"Agent 创建成功: {type(agent)}")
    print(f"LLM: {agent.llm}")
    print(f"Workflow: {agent.workflow}")
    print("✓ Agent 初始化测试通过\n")


def test_complex_curl():
    """测试复杂 curl 解析"""
    print("=" * 50)
    print("测试复杂 curl 解析")
    print("=" * 50)

    curl = """
    curl -X POST 'https://api.example.com/v1/stores/search?version=2' \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9' \
    -H 'X-Request-ID: 12345' \
    -d '{
        "keyword": "{{keyword}}",
        "city": "{{city}}",
        "district": "{{district}}",
        "category": "{{category}}",
        "pageSize": 20,
        "pageNum": 1
    }'
    """

    result = CurlParser.parse(curl)
    print(f"URL: {result.url}")
    print(f"Query Params: {result.query_params_template}")
    print(f"Method: {result.method}")
    print(f"Headers 数量: {len(result.headers)}")
    print(f"Placeholder Fields: {result.placeholder_fields}")

    assert "keyword" in result.placeholder_fields
    assert "city" in result.placeholder_fields
    assert "district" in result.placeholder_fields
    assert "category" in result.placeholder_fields
    print("✓ 复杂 curl 解析测试通过\n")


def test_edge_cases():
    """测试边界情况"""
    print("=" * 50)
    print("测试边界情况")
    print("=" * 50)

    # 测试空参数替换
    template = {"keyword": "{{keyword}}", "other": "value"}
    params = {}
    result = replace_placeholders(template, params)
    print(f"空参数替换: {result}")
    assert result["keyword"] == "{{keyword}}"  # 保留原样
    assert result["other"] == "value"
    print("✓ 空参数替换测试通过")

    # 测试 None 选择器
    data = {"key": "value"}
    result = extract_by_selector(data, None)
    assert result == data
    print("✓ None 选择器测试通过")

    # 测试空字符串选择器
    result = extract_by_selector(data, "")
    assert result == data
    print("✓ 空字符串选择器测试通过")

    # 测试不存在的路径
    result = extract_by_selector(data, "nonexistent.path")
    assert result is None
    print("✓ 不存在路径测试通过\n")


def test_agent_with_mock_run():
    """测试 Agent 运行（使用 mock）"""
    print("=" * 50)
    print("测试 Agent 运行（使用 mock）")
    print("=" * 50)

    mock_llm = MagicMock()
    mock_llm.model_name = "gpt-4o"
    mock_llm.temperature = 0.0

    # 模拟 LLM 响应
    mock_response = MagicMock()
    mock_response.content = '{"parameters": {"keyword": "星巴克", "city": "深圳"}, "reasoning": "从查询中提取"}'
    mock_llm.invoke.return_value = mock_response

    agent = QueryAgent(llm=mock_llm)

    # 使用 mock 替换工作流
    mock_result = {
        "is_satisfied": True,
        "final_result": {"id": 1, "name": "星巴克深圳店"},
        "final_raw_response": {"data": [{"id": 1, "name": "星巴克深圳店"}]},
        "final_reasoning": "找到匹配结果",
        "attempt_count": 1,
        "search_history": [],
        "current_parameters": {"keyword": "星巴克", "city": "深圳"}
    }
    agent.workflow = MagicMock()
    agent.workflow.invoke.return_value = mock_result

    # 执行查询
    result = agent.run(
        query="查找深圳的星巴克",
        curl="""
        curl -X POST 'https://api.example.com/search' \
        -H 'Content-Type: application/json' \
        -d '{"keyword": "{{keyword}}", "city": "{{city}}"}'
        """,
        system_prompt="查找门店信息"
    )

    assert result.success is True
    assert result.data is not None
    assert result.attempts == 1
    print(f"查询结果: success={result.success}, attempts={result.attempts}")
    print("✓ Agent 运行测试通过\n")


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Query Agent 测试套件")
    print("=" * 50 + "\n")

    try:
        test_curl_parser()
        test_replace_placeholders()
        test_extract_by_selector()
        test_agent_initialization()
        test_complex_curl()
        test_edge_cases()
        test_agent_with_mock_run()

        print("=" * 50)
        print("所有测试通过! ✓")
        print("=" * 50)
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
