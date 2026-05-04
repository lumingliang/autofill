#!/usr/bin/env python3
"""修复数据库中的模型名称"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.core.init_app import init_db
from app.models.llm_config import LLMConfig
from app.services.llm.litellm_sync_service import LiteLLMSyncService

async def fix_models():
    # 初始化数据库
    await init_db()
    
    # 修复 Qwen/QwQ-32B 的模型名称
    config = await LLMConfig.filter(name='Qwen/QwQ-32B').first()
    if config:
        print(f"修复配置: {config.name}")
        litellm_params = config.litellm_params or {}
        old_model = litellm_params.get('model', '')
        print(f"  原模型名称: {old_model}")
        
        # 更新为正确的模型名称
        litellm_params['model'] = 'Qwen/QwQ-32B'
        config.litellm_params = litellm_params
        await config.save()
        print(f"  新模型名称: Qwen/QwQ-32B")
    
    # 修复 DeepSeek-R1-0528 的模型名称
    config = await LLMConfig.filter(name='DeepSeek-R1-0528').first()
    if config:
        print(f"\n修复配置: {config.name}")
        litellm_params = config.litellm_params or {}
        old_model = litellm_params.get('model', '')
        print(f"  原模型名称: {old_model}")
        
        # 更新为正确的模型名称
        litellm_params['model'] = 'deepseek-ai/DeepSeek-R1-0528'
        config.litellm_params = litellm_params
        await config.save()
        print(f"  新模型名称: deepseek-ai/DeepSeek-R1-0528")
    
    # 同步到 LiteLLM 配置文件
    print("\n同步到 LiteLLM 配置文件...")
    sync_service = LiteLLMSyncService()
    await sync_service.sync_all_configs()
    print("✅ 同步完成")

if __name__ == "__main__":
    asyncio.run(fix_models())
