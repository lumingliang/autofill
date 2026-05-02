import asyncio
import httpx

async def test_direct_llm():
    """直接测试 LLM 调用（不通过代理）"""
    async with httpx.AsyncClient() as client:
        # 登录获取 token
        login_resp = await client.post('http://localhost:9999/api/v1/base/access_token', json={
            'username': 'admin',
            'password': '123456'
        })
        token = login_resp.json()['data']['access_token']
        print(f'Login success')
        
        # 获取配置列表
        configs_resp = await client.get(
            'http://localhost:9999/api/v1/ai/llm_config/list',
            headers={'token': token}
        )
        print(f'Configs: {configs_resp.json()}')
        
        # 测试配置连通性
        test_resp = await client.post(
            'http://localhost:9999/api/v1/ai/llm_config/test',
            json={'id': 1},
            headers={'token': token}
        )
        print(f'Test config response: {test_resp.status_code}')
        print(f'Test config data: {test_resp.json()}')

if __name__ == '__main__':
    asyncio.run(test_direct_llm())
