import asyncio
import httpx
import json

async def test_proxy():
    async with httpx.AsyncClient() as client:
        # 测试代理接口 - 结构化输出
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
            "preferred_methods": ["with_structured_output", "custom_fc_non_stream", "json_parser"],
            "config_name": "C4AI-Command-R-Plus"
        }
        
        # 使用 API Key 调用代理接口
        # 注意：这里需要一个有效的 API Key，我们先测试接口是否可用
        api_key = "test-api-key"
        
        try:
            proxy_resp = await client.post(
                'http://localhost:9999/api/api/llm/proxy',
                json=proxy_data,
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=60
            )
            print(f'Proxy response status: {proxy_resp.status_code}')
            print(f'Proxy response: {proxy_resp.text}')
        except Exception as e:
            print(f'Proxy error: {e}')

if __name__ == '__main__':
    asyncio.run(test_proxy())
