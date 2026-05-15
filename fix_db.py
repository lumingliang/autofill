#!/usr/bin/env python3
"""修复数据库中的脱敏 API key"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.core.init_app import init_db
from app.models.llm_config import LLMConfig

# 正确的 API key
CORRECT_API_KEY = "ms-919b1188-52f3-4654-b3bd-c46ab3bcf738"

async def fix_configs():
    # 初始化数据库
    await init_db()

    configs = await LLMConfig.filter(is_active=True).all()
    for config in configs:
        litellm_params = config.litellm_params or {}
        api_key = litellm_params.get('api_key', '')

        if '****' in api_key or '••••' in api_key:
            print(f"修复配置: {config.name}")
            print(f"  原 API key: {api_key}")

            # 更新为正确的 API key
            litellm_params['api_key'] = CORRECT_API_KEY
            config.litellm_params = litellm_params
            await config.save()

            print(f"  新 API key: {CORRECT_API_KEY}")
        else:
            print(f"配置 {config.name} 的 API key 正常: {api_key[:10]}...{api_key[-4:]}")

if __name__ == "__main__":
    asyncio.run(fix_configs())
