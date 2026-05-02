#!/usr/bin/env python3
"""
调试 Query Agent 的 curl 解析和参数提取
"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.services.query_agent.parser import CurlParser

# 测试 curl 命令
CURL_COMMAND = """curl -X POST 'http://localhost:9999/api/v1/byd-dealers/public/byd-dealers/search' \
-H 'Content-Type: application/json' \
-d '{
    "app_key": "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR",
    "query": "{{name}}",
    "city": "{{city}}",
    "limit": 10
}'"""

print("=" * 70)
print("调试: Curl 解析")
print("=" * 70)
print(f"\n原始 Curl 命令:\n{CURL_COMMAND}")

# 解析 curl
parsed = CurlParser.parse(CURL_COMMAND)

print(f"\n解析结果:")
print(f"  URL: {parsed.url}")
print(f"  Method: {parsed.method}")
print(f"  Headers: {parsed.headers}")
print(f"  Body Template: {parsed.body_template}")
print(f"  Query Params: {parsed.query_params_template}")
print(f"  Placeholder Fields: {parsed.placeholder_fields}")
print(f"  Param Schema: {parsed.param_schema}")

print("\n" + "=" * 70)
print("调试: 参数替换")
print("=" * 70)

# 测试参数替换
from app.services.query_agent.utils import replace_placeholders_in_curl

test_params = {
    "name": "体验中心4号",
    "city": "上海"
}

print(f"\n测试参数: {test_params}")
result_curl = replace_placeholders_in_curl(CURL_COMMAND, test_params)
print(f"\n替换后的 Curl:\n{result_curl}")

# 验证替换后的 curl 是否能正常解析
print("\n" + "=" * 70)
print("调试: 验证替换后的 curl")
print("=" * 70)

try:
    parsed_result = CurlParser.parse(result_curl)
    print(f"\n替换后的 Body Template: {parsed_result.body_template}")
except Exception as e:
    print(f"\n解析失败: {e}")
