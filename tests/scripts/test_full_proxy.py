import asyncio
import httpx
import json

async def test_full_proxy():
    """测试完整的代理接口（结构化输出）"""
    async with httpx.AsyncClient() as client:
    
        
        # 2. 调用代理接口（使用应用的 API Key 认证）
        api_key = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
        
        proxy_data = {
            "query": "请提取以下信息：姓名张三，年龄25岁，邮箱zhangsan@example.com",
            "tools": [
                {
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
            ],
            "system_prompt": "你是一个信息提取助手，请从用户输入中提取结构化信息。",
            "preferred_methods": ["with_structured_output", "custom_fc_non_stream", "json_parser"]
        }
        
        print("\nTesting proxy API with structured output...")
        print(f"Using API Key: {api_key[:10]}...")
        
        try:
            proxy_resp = await client.post(
                'http://localhost:9999/api/llm/proxy',
                json=proxy_data,
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=60
            )
            print(f'Proxy response status: {proxy_resp.status_code}')
            result = proxy_resp.json()
            print(f'Proxy response: {json.dumps(result, indent=2, ensure_ascii=False)}')
            
            if result.get('code') == 200:
                print("\n✓ Proxy API structured output test PASSED!")
                data = result.get('data', {})
                print(f"Method used: {data.get('method')}")
                print(f"Result data: {json.dumps(data.get('data'), indent=2, ensure_ascii=False)}")
            else:
                print(f"\n✗ Proxy API test failed: {result.get('msg')}")
                
        except Exception as e:
            print(f'Error: {e}')

if __name__ == '__main__':
    asyncio.run(test_full_proxy())
