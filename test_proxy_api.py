import asyncio
import httpx
import json

async def test_proxy_api():
    """测试应用代理接口"""
    async with httpx.AsyncClient() as client:
        # 1. 登录获取管理 token
        login_resp = await client.post('http://localhost:9999/api/v1/base/access_token', json={
            'username': 'admin',
            'password': '123456'
        })
        token = login_resp.json()['data']['access_token']
        print(f'Login success')
        
        # 2. 获取网关状态
        gateway_resp = await client.get(
            'http://localhost:9999/api/v1/ai/llm_config/gateway/status',
            headers={'token': token}
        )
        print(f'Gateway status: {gateway_resp.json()}')
        
        # 3. 测试配置连通性（通过 LiteLLM 网关）
        test_resp = await client.post(
            'http://localhost:9999/api/v1/ai/llm_config/test',
            json={'id': 1},
            headers={'token': token}
        )
        print(f'Test config response: {test_resp.status_code}')
        print(f'Test config data: {test_resp.json()}')

if __name__ == '__main__':
    asyncio.run(test_proxy_api())
