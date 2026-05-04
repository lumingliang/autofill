#!/usr/bin/env python3
"""直接测试 LiteLLM 网关的 function calling"""
import asyncio
import httpx
import json

async def test_function_calling():
    base_url = "http://localhost:4000"
    master_key = "sk-litellm-master-key"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {master_key}"
    }
    
    tools = [{
        "type": "function",
        "function": {
            "name": "search_store",
            "description": "搜索门店信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "门店名称"
                    },
                    "city": {
                        "type": "string",
                        "description": "城市"
                    }
                },
                "required": ["name", "city"]
            }
        }
    }]
    
    messages = [
        {"role": "system", "content": "你是一个 helpful 助手。当用户需要搜索门店时，请使用 search_store 工具。"},
        {"role": "user", "content": "帮我找一下重庆的比亚迪门店"}
    ]
    
    payload = {
        "model": "DeepSeek-R1-0528",
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto"
    }
    
    print("=" * 80)
    print("测试 LiteLLM 网关 Function Calling")
    print("=" * 80)
    print(f"\n请求:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=60
            )
            
            print(f"\n状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n响应:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                
                # 检查是否有 tool_calls
                message = result.get("choices", [{}])[0].get("message", {})
                tool_calls = message.get("tool_calls", [])
                content = message.get("content", "")
                
                print("\n" + "=" * 80)
                if tool_calls:
                    print("✅ 检测到标准 tool_calls:")
                    print(json.dumps(tool_calls, indent=2, ensure_ascii=False))
                else:
                    print("❌ 没有标准 tool_calls")
                    if content:
                        print(f"\n返回的 content:\n{content}")
            else:
                print(f"\n❌ 请求失败: {response.text}")
                
    except Exception as e:
        print(f"\n❌ 错误: {e}")

if __name__ == "__main__":
    asyncio.run(test_function_calling())
