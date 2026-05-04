#!/usr/bin/env python3
"""检查数据库中的 LLM 配置数据"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.core.init_app import init_db
from app.models.llm_config import LLMConfig

async def check_configs():
    # 初始化数据库
    await init_db()

    configs = await LLMConfig.filter(is_active=True).all()
    for config in configs:
        print(f"\n配置名称: {config.name}")
        print(f"litellm_params: {config.litellm_params}")
        api_key = config.litellm_params.get('api_key', '')
        if api_key:
            if '****' in api_key or '••••' in api_key:
                print(f"⚠️  API key 被脱敏: {api_key}")
            else:
                print(f"✅ API key 正常: {api_key[:10]}...{api_key[-4:]}")
        else:
            print("⚠️  API key 为空")

if __name__ == "__main__":
    asyncio.run(check_configs())
