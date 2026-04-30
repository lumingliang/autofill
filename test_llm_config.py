import asyncio
import httpx

async def create_config():
    async with httpx.AsyncClient() as client:
        # 登录获取 token
        login_resp = await client.post('http://localhost:9999/api/v1/base/access_token', json={
            'username': 'admin',
            'password': '123456'
        })
        token = login_resp.json()['data']['access_token']
        print(f'Login success')
        
        # 创建 LLM 配置，使用租户ID=1
        config_data = {
            'name': 'C4AI-Command-R-Plus',
            'model_provider': 'openai',
            'model_name': 'LLM-Research/c4ai-command-r-plus-08-2024',
            'api_key': 'ms-919b1188-52f3-4654-b3bd-c46ab3bcf738',
            'api_base': 'https://api-inference.modelscope.cn/v1/',
            'timeout': 60,
            'is_active': True,
            'is_default': True,
            'description': 'ModelScope C4AI Command R Plus',
            'tenant_id': 1
        }
        
        create_resp = await client.post(
            'http://localhost:9999/api/v1/ai/llm_config/create',
            json=config_data,
            headers={'token': token}
        )
        print(f'Create config response: {create_resp.status_code}')
        print(f'Create config data: {create_resp.json()}')

if __name__ == '__main__':
    asyncio.run(create_config())
