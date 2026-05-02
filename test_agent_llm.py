#!/usr/bin/env python3
"""
调试 Query Agent 的 LLM 调用
"""
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

import json
from app.core.config import settings
from langchain_openai import ChatOpenAI

# 测试 LLM 调用
print("=" * 70)
print("调试: LLM Function Calling")
print("=" * 70)

# 使用 LiteLLM 网关配置
litellm_config = settings.LITELLM_CONFIG
base_url = litellm_config.get("base_url", "http://localhost:4000")
master_key = litellm_config.get("master_key", "")

print(f"\nLiteLLM 配置:")
print(f"  Base URL: {base_url}")
print(f"  Master Key: {'*' * len(master_key) if master_key else '未设置'}")

# 创建 LLM 实例
llm = ChatOpenAI(
    model="C4AI-Command-R-Plus",
    api_key=master_key,
    base_url=f"{base_url}/v1",
    temperature=0.0,
    timeout=60
)

# 构建 tools
tools = [
    {
        "type": "function",
        "function": {
            "name": "extract_search_params",
            "description": "从用户输入中提取搜索参数，用于调用 http://localhost:9999/api/v1/byd-dealers/public/byd-dealers/search 接口",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "query参数的值（从用户输入中提取）"
                    },
                    "city": {
                        "type": "string",
                        "description": "city参数的值（从用户输入中提取）"
                    }
                },
                "required": ["name", "city"]
            }
        }
    }
]

# 用户输入
query = """用户：我今天到你们上海体验中心店修车的时候那个服务人员态度极差
客服：好的。我帮您查一下，是哪个店？
用户：4号店。"""

system_prompt = """你是一个比亚迪门店查询助手。你的任务是从用户的聊天记录中提取关键信息，并决定如何调用搜索接口。

请仔细分析用户的输入，提取最准确的参数值，以便能够查询到正确的结果。"""

print(f"\n用户输入:\n{query}")
print(f"\nSystem Prompt:\n{system_prompt}")

# 调用 LLM
try:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ]

    print("\n调用 LLM...")
    response = llm.invoke(
        messages,
        tools=tools,
        tool_choice={"type": "function", "function": {"name": "extract_search_params"}}
    )

    print(f"\nLLM 响应:")
    print(f"  Content: {response.content}")
    print(f"  Additional Kwargs: {json.dumps(response.additional_kwargs, indent=2, ensure_ascii=False)}")

    # 提取函数调用参数
    tool_calls = response.additional_kwargs.get("tool_calls", [])
    if tool_calls:
        function_args = json.loads(tool_calls[0]["function"]["arguments"])
        print(f"\n提取的参数: {json.dumps(function_args, indent=2, ensure_ascii=False)}")
    else:
        print("\n没有 tool_calls")

except Exception as e:
    print(f"\nLLM 调用失败: {e}")
    import traceback
    traceback.print_exc()
