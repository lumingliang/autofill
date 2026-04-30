import asyncio
import httpx
import json

async def test_structured_output():
    """通过 LiteLLM 网关测试结构化输出"""
    async with httpx.AsyncClient() as client:
        # 测试 function calling
        proxy_data = {
            "model": "C4AI-Command-R-Plus",
            "messages": [
                {"role": "system", "content": "你是一个信息提取助手，请从用户输入中提取结构化信息。"},
                {"role": "user", "content": "请提取以下信息：姓名张三，年龄25岁，邮箱zhangsan@example.com"}
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "extract_person_info",
                        "description": "提取人员信息",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "姓名"
                                },
                                "age": {
                                    "type": "integer",
                                    "description": "年龄"
                                },
                                "email": {
                                    "type": "string",
                                    "description": "邮箱"
                                }
                            },
                            "required": ["name", "age", "email"]
                        }
                    }
                }
            ],
            "tool_choice": {"type": "function", "function": {"name": "extract_person_info"}},
            "max_tokens": 200
        }
        
        try:
            response = await client.post(
                'http://localhost:4000/v1/chat/completions',
                json=proxy_data,
                headers={
                    'Authorization': 'Bearer sk-litellm-master-key',
                    'Content-Type': 'application/json'
                },
                timeout=60
            )
            print(f'Response status: {response.status_code}')
            result = response.json()
            print(f'Response: {json.dumps(result, indent=2, ensure_ascii=False)}')
            
            # 检查是否有 tool_calls
            if 'choices' in result and len(result['choices']) > 0:
                message = result['choices'][0].get('message', {})
                tool_calls = message.get('tool_calls', [])
                if tool_calls:
                    print(f"\n✓ Function calling works!")
                    print(f"Tool calls: {json.dumps(tool_calls, indent=2, ensure_ascii=False)}")
                else:
                    content = message.get('content', '')
                    print(f"\nContent: {content}")
                    print("Note: Model returned content instead of tool_calls")
                    
        except Exception as e:
            print(f'Error: {e}')

if __name__ == '__main__':
    asyncio.run(test_structured_output())
