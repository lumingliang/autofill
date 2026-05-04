#!/usr/bin/env python3
"""测试使用不同模型名称的 function calling"""
import asyncio
import httpx
import json

async def test_with_model(model_name):
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
                    "name": {"type": "string", "description": "门店名称"},
                    "city": {"type": "string", "description": "城市"}
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
        "model": model_name,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto"
    }
    
    print(f"\n测试模型: {model_name}")
    print("-" * 80)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                message = result.get("choices", [{}])[0].get("message", {})
                tool_calls = message.get("tool_calls", [])
                content = message.get("content", "")
                
                if tool_calls:
                    print(f"✅ 成功 - 检测到 {len(tool_calls)} 个 tool_calls")
                    args = json.loads(tool_calls[0].get("function", {}).get("arguments", "{}"))
                    print(f"   参数: {args}")
                else:
                    print(f"❌ 失败 - 没有 tool_calls")
                    if content:
                        print(f"   content: {content[:200]}...")
            else:
                print(f"❌ 请求失败: {response.status_code}")
                print(f"   {response.text[:200]}")
                
    except Exception as e:
        print(f"❌ 错误: {e}")

async def main():
    print("=" * 80)
    print("测试不同模型名称的 Function Calling")
    print("=" * 80)
    
    # 测试不同的模型名称
    await test_with_model("DeepSeek-R1-0528")
    await test_with_model("openai/deepseek-ai/DeepSeek-R1-0528")

if __name__ == "__main__":
    asyncio.run(main())
