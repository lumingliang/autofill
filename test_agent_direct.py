#!/usr/bin/env python3
"""
直接测试 Query Agent 接口
测试场景：用户和客服的聊天记录查询比亚迪门店
Agent 通过 FC 调用决定 curl 请求的参数值
"""
import asyncio
import httpx
import sys

# 后端地址
BASE_URL = "http://localhost:9999"

# API Key（使用现有的应用）
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"

# 测试场景
TEST_CHAT = """用户：我今天到你们上海体验中心店修车的时候那个服务人员态度极差
客服：好的。我帮您查一下，是哪个店？
用户：4号店。"""

# 构造 curl 命令模板（参数值由 Agent 通过 FC 调用决定）
# 这个 curl 包含三个参数：name, city, address
CURL_TEMPLATE = f"""curl -X POST '{BASE_URL}/api/v1/byd-dealers/public/byd-dealers/search' \
-H 'Content-Type: application/json' \
-d '{{
    "app_key": "{API_KEY}",
    "query": "{{{{name}}}}",
    "city": "{{{{city}}}}",
    "limit": 10
}}'"""

# System Prompt - 指导 LLM 从聊天记录中提取参数
# 注意：FC 调用的参数结构会根据 curl 模板动态生成，不需要在这里定义
SYSTEM_PROMPT = """你是一个比亚迪门店查询助手。你的任务是从用户的聊天记录中提取关键信息，用于搜索门店。

请仔细分析用户的输入，提取以下信息：
1. 城市名称（如上海、北京、深圳等）
2. 门店名称关键词（如体验中心、4号店、王朝网等）
3. 地址信息（如果有）

要求：
- 参数值应该从聊天记录中直接提取
- 如果信息不完整，使用最可能的关键词
- 返回最匹配的门店信息"""


async def test_agent_query():
    """测试 Query Agent 接口"""
    print("=" * 70)
    print("测试: Query Agent 查询比亚迪门店")
    print("=" * 70)
    print(f"\n聊天记录:\n{TEST_CHAT}")
    print(f"\nCurl 模板:\n{CURL_TEMPLATE}")
    print(f"\nSystem Prompt:\n{SYSTEM_PROMPT}")

    # 构造请求参数
    agent_request = {
        "query": TEST_CHAT,
        "curl": CURL_TEMPLATE.strip(),
        "system_prompt": SYSTEM_PROMPT,
        "max_attempts": 2,
        "timeout": 60,
        "llm_model": "C4AI-Command-R-Plus",
        "llm_temperature": 0.0,
        "return_raw_response": True,
        "result_selector": "data.0"
    }

    print("\n" + "=" * 70)
    print("发送请求到 /api/agent/query")
    print("=" * 70)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:
        try:
            response = await client.post(
                "/api/agent/query",
                json=agent_request
            )

            print(f"\n响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"\n✓ Agent 查询成功")
                print(f"  - 尝试次数: {result.get('attempts', 0)}")
                print(f"  - 是否满意: {result.get('is_satisfied', False)}")
                print(f"  - 推理: {result.get('reasoning', '')}")

                data = result.get('data')
                if data:
                    print(f"\n  ✓ 找到匹配门店:")
                    print(f"    名称: {data.get('name', 'N/A')}")
                    print(f"    城市: {data.get('city', 'N/A')}")
                    print(f"    地址: {data.get('address', 'N/A')}")
                    print(f"    电话: {data.get('phone', 'N/A')}")
                    print(f"    类型: {data.get('dealer_type', 'N/A')}")

                    # 验证是否匹配预期
                    name = data.get('name', '')
                    city = data.get('city', '')
                    if '上海' in city and '体验中心' in name and '4' in name:
                        print(f"\n  ✓✓✓ 成功匹配预期门店（上海体验中心4号店）!")
                        return True
                    else:
                        print(f"\n  ⚠ 未完全匹配预期（预期: 上海体验中心4号店）")
                        return False
                else:
                    print(f"\n  ✗ 未找到匹配门店")
                    return False

            else:
                print(f"✗ Agent 查询失败: {response.status_code}")
                print(f"响应: {response.text[:500]}")
                return False

        except Exception as e:
            print(f"✗ 测试异常: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """主函数"""
    success = await test_agent_query()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
