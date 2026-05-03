"""
Agent 测试工具函数
"""
import json
import requests
from dataclasses import dataclass
from typing import Dict, Any, Optional, Callable

from tests.conftest import BASE_URL, API_KEY, get_default_headers, DEFAULT_TIMEOUT, DEFAULT_SYSTEM_PROMPT, DEFAULT_EXPECTED_RESULT


@dataclass
class TestResult:
    """测试结果数据类"""
    name: str
    success: bool
    message: str = ""
    data: Dict[str, Any] = None
    attempts: int = 0

    def __post_init__(self):
        if self.data is None:
            self.data = {}


class AgentTestClient:
    """Agent 测试客户端"""

    def __init__(self, base_url: str = BASE_URL, api_key: str = API_KEY):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = get_default_headers()

    def build_curl_template(self, endpoint: str = "/api/byd-dealers/search") -> str:
        """构建 curl 模板"""
        return f"""curl -X POST '{self.base_url}{endpoint}' -H 'Content-Type: application/json' -H 'Authorization: Bearer {self.api_key}' -d '{{"app_key": "{self.api_key}", "name": "", "city": "", "address": "", "limit": 10}}'"""

    def build_agent_payload(
        self,
        query: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        expected_result: str = DEFAULT_EXPECTED_RESULT,
        max_attempts: int = 3,
        timeout: int = 30,
        endpoint: str = "/api/byd-dealers/search"
    ) -> Dict[str, Any]:
        """构建 Agent 请求体"""
        curl_template = self.build_curl_template(endpoint)
        return {
            "query": query,
            "curl": curl_template,
            "system_prompt": system_prompt,
            "expected_result": expected_result,
            "max_attempts": max_attempts,
            "timeout": timeout
        }

    def query_agent(
        self,
        query: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        expected_result: str = DEFAULT_EXPECTED_RESULT,
        max_attempts: int = 3,
        timeout: int = 30,
        endpoint: str = "/api/byd-dealers/search"
    ) -> TestResult:
        """调用 Agent 查询接口"""
        url = f"{self.base_url}/api/v1/agent/query"
        payload = self.build_agent_payload(
            query=query,
            system_prompt=system_prompt,
            expected_result=expected_result,
            max_attempts=max_attempts,
            timeout=timeout,
            endpoint=endpoint
        )

        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=DEFAULT_TIMEOUT
            )
            data = response.json()

            if data.get('success') and data.get('data', {}).get('success'):
                dealers = data['data'].get('data', [])
                return TestResult(
                    name="Agent 查询",
                    success=True,
                    message=f"找到 {len(dealers)} 家门店",
                    data=data,
                    attempts=data.get('total_attempts', 0)
                )
            else:
                return TestResult(
                    name="Agent 查询",
                    success=False,
                    message=data.get('error', '未知错误'),
                    data=data,
                    attempts=data.get('total_attempts', 0)
                )
        except Exception as e:
            return TestResult(
                name="Agent 查询",
                success=False,
                message=str(e),
                attempts=0
            )

    def search_dealers(
        self,
        name: str = "",
        city: str = "",
        address: str = "",
        limit: int = 5
    ) -> TestResult:
        """直接搜索经销商"""
        url = f"{self.base_url}/api/byd-dealers/search"
        payload = {
            "app_key": self.api_key,
            "name": name,
            "city": city,
            "address": address,
            "limit": limit
        }

        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=DEFAULT_TIMEOUT
            )
            data = response.json()

            if data.get("success") and data.get("total", 0) > 0:
                return TestResult(
                    name="经销商搜索",
                    success=True,
                    message=f"找到 {data['total']} 家门店",
                    data=data
                )
            else:
                return TestResult(
                    name="经销商搜索",
                    success=False,
                    message=data.get('message', '未找到门店'),
                    data=data
                )
        except Exception as e:
            return TestResult(
                name="经销商搜索",
                success=False,
                message=str(e)
            )


def print_test_header(title: str):
    """打印测试标题"""
    print("\n" + "=" * 80)
    print(f"测试: {title}")
    print("=" * 80)


def print_test_result(result: TestResult):
    """打印测试结果"""
    status = "✅ 通过" if result.success else "❌ 失败"
    print(f"\n{status} - {result.name}")
    if result.message:
        print(f"  消息: {result.message}")
    if result.attempts > 0:
        print(f"  尝试次数: {result.attempts}")


def run_test_case(name: str, test_func: Callable[[], TestResult]) -> TestResult:
    """运行单个测试用例"""
    print_test_header(name)
    try:
        result = test_func()
        print_test_result(result)
        return result
    except Exception as e:
        result = TestResult(name=name, success=False, message=f"异常: {str(e)}")
        print_test_result(result)
        return result


def build_curl_template(base_url: str = BASE_URL, api_key: str = API_KEY) -> str:
    """构建 curl 模板（向后兼容）"""
    client = AgentTestClient(base_url=base_url, api_key=api_key)
    return client.build_curl_template()


def build_agent_payload(
    query: str,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    expected_result: str = DEFAULT_EXPECTED_RESULT,
    max_attempts: int = 3,
    timeout: int = 30
) -> Dict[str, Any]:
    """构建 Agent 请求体（向后兼容）"""
    client = AgentTestClient()
    return client.build_agent_payload(
        query=query,
        system_prompt=system_prompt,
        expected_result=expected_result,
        max_attempts=max_attempts,
        timeout=timeout
    )
