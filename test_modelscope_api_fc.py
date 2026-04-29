#!/usr/bin/env python3
"""
直接测试魔搭社区 API 的 Function Calling 支持
"""

import asyncio
import json
from openai import AsyncOpenAI


async def test_modelscope_fc():
    """测试魔搭社区 API 的 FC 支持"""
    
    client = AsyncOpenAI(
        api_key="ms-919b1188-52f3-4654-b3bd-c46ab3bcf738",
        base_url="https://api-inference.modelscope.cn/v1/"
    )
    
    # 测试 1: 非流式 + tools
    print("测试 1: 非流式调用 + tools 参数")
    try:
        response = await client.chat.completions.create(
            model="Qwen/QwQ-32B",
            messages=[
                {"role": "system", "content": "你是一个信息提取助手。"},
                {"role": "user", "content": "客户张三说他的2024款极越01充电到80%就停了。"}
            ],
            tools=[{
                "type": "function",
                "function": {
                    "name": "extract_customer_info",
                    "description": "提取客户信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_name": {"type": "string"},
                            "vehicle_model": {"type": "string"},
                            "issue": {"type": "string"}
                        },
                        "required": ["customer_name"]
                    }
                }
            }],
            tool_choice="auto"
        )
        print(f"响应: {json.dumps(response.model_dump(), ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    # 测试 2: 流式 + tools
    print("\n测试 2: 流式调用 + tools 参数")
    try:
        stream = await client.chat.completions.create(
            model="Qwen/QwQ-32B",
            messages=[
                {"role": "system", "content": "你是一个信息提取助手。"},
                {"role": "user", "content": "客户张三说他的2024款极越01充电到80%就停了。"}
            ],
            tools=[{
                "type": "function",
                "function": {
                    "name": "extract_customer_info",
                    "description": "提取客户信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_name": {"type": "string"},
                            "vehicle_model": {"type": "string"},
                            "issue": {"type": "string"}
                        },
                        "required": ["customer_name"]
                    }
                }
            }],
            tool_choice="auto",
            stream=True
        )
        
        content = ""
        tool_calls = []
        async for chunk in stream:
            print(f"Chunk: {json.dumps(chunk.model_dump(), ensure_ascii=False)}")
            if chunk.choices and chunk.choices[0].delta:
                delta = chunk.choices[0].delta
                if delta.content:
                    content += delta.content
                if delta.tool_calls:
                    tool_calls.extend(delta.tool_calls)
        
        print(f"\n内容: {content}")
        print(f"工具调用: {tool_calls}")
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试 3: 流式 + JSON 模式
    print("\n测试 3: 流式调用 + JSON 模式")
    try:
        stream = await client.chat.completions.create(
            model="Qwen/QwQ-32B",
            messages=[
                {"role": "system", "content": "你是一个信息提取助手。请返回JSON格式。"},
                {"role": "user", "content": "客户张三说他的2024款极越01充电到80%就停了。"}
            ],
            response_format={"type": "json_object"},
            stream=True
        )
        
        content = ""
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content += chunk.choices[0].delta.content
        
        print(f"内容: {content}")
        data = json.loads(content)
        print(f"解析后的数据: {data}")
    except Exception as e:
        print(f"❌ 失败: {e}")


if __name__ == "__main__":
    asyncio.run(test_modelscope_fc())
