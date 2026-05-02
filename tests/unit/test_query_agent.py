"""
Query Agent 测试用例
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock

from app.services.query_agent import (
    QueryAgent,
    QueryAgentInput,
    CurlParser,
    ParsedCurl,
    CurlParseError
)
from app.services.query_agent.utils import (
    replace_placeholders,
    extract_by_selector,
    clean_json_response
)


class TestCurlParser:
    """测试 Curl 解析器"""

    def test_parse_simple_get(self):
        """测试简单的 GET 请求"""
        curl = "curl https://api.example.com/users"
        result = CurlParser.parse(curl)

        assert result.url == "https://api.example.com/users"
        assert result.method == "GET"
        assert result.headers == {}
        assert result.body_template is None

    def test_parse_post_with_body(self):
        """测试带 body 的 POST 请求"""
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

        assert result.url == "https://api.example.com/search"
        assert result.method == "POST"
        assert result.headers["Content-Type"] == "application/json"
        assert result.headers["Authorization"] == "Bearer token123"
        assert result.body_template is not None
        assert "{{keyword}}" in result.body_template.get("keyword", "")
        assert result.placeholder_fields == ["keyword", "city"]

    def test_parse_with_query_params(self):
        """测试带查询参数的 URL"""
        curl = "curl 'https://api.example.com/search?page=1&size=10'"
        result = CurlParser.parse(curl)

        assert result.url == "https://api.example.com/search"
        assert result.query_params_template == {"page": "1", "size": "10"}

    def test_parse_empty_curl(self):
        """测试空 curl"""
        with pytest.raises(CurlParseError):
            CurlParser.parse("")

    def test_parse_without_url(self):
        """测试没有 URL 的 curl"""
        with pytest.raises(CurlParseError):
            CurlParser.parse("curl -X POST")


class TestUtils:
    """测试工具函数"""

    def test_replace_placeholders_in_dict(self):
        """测试替换字典中的占位符"""
        template = {
            "keyword": "{{keyword}}",
            "city": "{{city}}",
            "nested": {
                "name": "{{name}}"
            }
        }
        parameters = {
            "keyword": "星巴克",
            "city": "深圳",
            "name": "test"
        }
        result = replace_placeholders(template, parameters)

        assert result["keyword"] == "星巴克"
        assert result["city"] == "深圳"
        assert result["nested"]["name"] == "test"

    def test_replace_placeholders_in_string(self):
        """测试替换字符串中的占位符"""
        template = "Hello {{name}}, welcome to {{city}}!"
        parameters = {"name": "Alice", "city": "Beijing"}
        result = replace_placeholders(template, parameters)

        assert result == "Hello Alice, welcome to Beijing!"

    def test_replace_placeholders_keep_unknown(self):
        """测试保留未知的占位符"""
        template = {"keyword": "{{keyword}}", "unknown": "{{unknown}}"}
        parameters = {"keyword": "test"}
        result = replace_placeholders(template, parameters)

        assert result["keyword"] == "test"
        assert result["unknown"] == "{{unknown}}"

    def test_extract_by_selector_dot_path(self):
        """测试点号路径选择器"""
        data = {
            "data": {
                "items": [
                    {"id": 1, "name": "item1"},
                    {"id": 2, "name": "item2"}
                ],
                "total": 100
            }
        }
        result = extract_by_selector(data, "data.items")
        assert len(result) == 2
        assert result[0]["name"] == "item1"

    def test_extract_by_selector_array_index(self):
        """测试数组索引选择器"""
        data = {
            "items": [
                {"id": 1, "name": "item1"},
                {"id": 2, "name": "item2"}
            ]
        }
        result = extract_by_selector(data, "items.0")
        assert result["name"] == "item1"

    def test_extract_by_selector_jsonpath(self):
        """测试 JSONPath 选择器"""
        data = {
            "data": {
                "items": [
                    {"id": 1, "name": "item1"}
                ]
            }
        }
        result = extract_by_selector(data, "$.data.items[0]")
        assert result["name"] == "item1"

    def test_clean_json_response(self):
        """测试清理 JSON 响应"""
        content = "```json\n{\"key\": \"value\"}\n```"
        result = clean_json_response(content)
        assert result == '{"key": "value"}'

    def test_clean_json_response_no_markers(self):
        """测试没有标记的响应"""
        content = '{"key": "value"}'
        result = clean_json_response(content)
        assert result == '{"key": "value"}'


class TestQueryAgent:
    """测试 QueryAgent"""

    @patch('app.services.query_agent.agent.ChatOpenAI')
    def test_agent_initialization(self, mock_llm_class):
        """测试 Agent 初始化"""
        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm

        agent = QueryAgent()
        assert agent is not None
        assert agent.llm is not None

    @patch('app.services.query_agent.agent.ChatOpenAI')
    def test_run_with_mock(self, mock_llm_class):
        """测试带 mock 的运行"""
        # 设置 mock
        mock_llm = MagicMock()
        mock_llm.model_name = "gpt-4o"
        mock_llm.temperature = 0.0

        # 模拟 LLM 响应
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "parameters": {"keyword": "星巴克", "city": "深圳"},
            "reasoning": "从查询中提取"
        })
        mock_llm.invoke.return_value = mock_response
        mock_llm_class.return_value = mock_llm

        # 创建 agent
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

    @patch('app.services.query_agent.agent.ChatOpenAI')
    def test_run_with_result_selector(self, mock_llm_class):
        """测试带结果选择器的运行"""
        mock_llm = MagicMock()
        mock_llm.model_name = "gpt-4o"
        mock_llm.temperature = 0.0
        mock_llm_class.return_value = mock_llm

        agent = QueryAgent(llm=mock_llm)

        # 模拟返回嵌套结构的数据
        mock_result = {
            "is_satisfied": True,
            "final_result": {
                "data": {
                    "items": [
                        {"id": 1, "name": "item1"},
                        {"id": 2, "name": "item2"}
                    ],
                    "total": 2
                }
            },
            "final_raw_response": None,
            "final_reasoning": "找到结果",
            "attempt_count": 1,
            "search_history": [],
            "current_parameters": {}
        }
        agent.workflow = MagicMock()
        agent.workflow.invoke.return_value = mock_result

        # 使用 result_selector 提取嵌套数据
        result = agent.run(
            query="测试查询",
            curl="curl https://api.example.com/test",
            system_prompt="测试",
            result_selector="data.items"
        )

        # 验证结果是否被正确提取
        assert result.success is True
        assert isinstance(result.data, list)
        assert len(result.data) == 2

    @patch('app.services.query_agent.agent.ChatOpenAI')
    def test_run_with_custom_params(self, mock_llm_class):
        """测试带自定义参数的运行"""
        mock_llm = MagicMock()
        mock_llm.model_name = "gpt-4o"
        mock_llm.temperature = 0.0
        mock_llm_class.return_value = mock_llm

        agent = QueryAgent(llm=mock_llm)

        # 验证自定义参数被正确传递
        mock_result = {
            "is_satisfied": False,
            "final_result": None,
            "final_raw_response": None,
            "final_reasoning": "未找到",
            "attempt_count": 3,
            "search_history": [],
            "current_parameters": {}
        }
        agent.workflow = MagicMock()
        agent.workflow.invoke.return_value = mock_result

        result = agent.run(
            query="测试查询",
            curl="curl https://api.example.com/test",
            system_prompt="测试",
            max_attempts=3,
            timeout=60,
            llm_model="gpt-4o-mini",
            llm_temperature=0.5,
            return_raw_response=True
        )

        assert result.attempts == 3

    @patch('app.services.query_agent.agent.ChatOpenAI')
    def test_run_with_input_object(self, mock_llm_class):
        """测试使用输入对象运行"""
        mock_llm = MagicMock()
        mock_llm.model_name = "gpt-4o"
        mock_llm.temperature = 0.0
        mock_llm_class.return_value = mock_llm

        agent = QueryAgent(llm=mock_llm)

        mock_result = {
            "is_satisfied": True,
            "final_result": {"id": 1},
            "final_raw_response": None,
            "final_reasoning": "找到",
            "attempt_count": 1,
            "search_history": [],
            "current_parameters": {}
        }
        agent.workflow = MagicMock()
        agent.workflow.invoke.return_value = mock_result

        input_data = QueryAgentInput(
            query="测试查询",
            curl="curl https://api.example.com/test",
            system_prompt="测试",
            max_attempts=2,
            timeout=45
        )

        result = agent.run_with_input(input_data)

        assert result.success is True


class TestIntegration:
    """集成测试（需要外部服务）"""

    @pytest.mark.skip(reason="需要外部 API 服务")
    def test_real_api_call(self):
        """测试真实 API 调用"""
        # 这个测试需要真实的外部 API
        pass


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
