#!/usr/bin/env python3
"""同步配置到 LiteLLM 的 config.yaml"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.core.init_app import init_db
from app.services.llm.litellm_sync_service import LiteLLMSyncService

async def sync():
    await init_db()
    
    print("同步配置到 LiteLLM config.yaml...")
    sync_service = LiteLLMSyncService()
    result = await sync_service.sync_all_configs()
    
    if result:
        print("✅ 同步成功")
    else:
        print("❌ 同步失败")

if __name__ == "__main__":
    asyncio.run(sync())
