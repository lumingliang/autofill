#!/usr/bin/env python3
"""
查询可用的 API Key
"""
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

import asyncio
from tortoise import Tortoise
from app.settings.config import settings

async def init_tortoise():
    """初始化 Tortoise ORM"""
    await Tortoise.init(
        db_url=settings.DATABASE_URL,
        modules={'models': settings.TORTOISE_MODELS}
    )

async def check_api_keys():
    """查询可用的 API Key"""
    await init_tortoise()
    
    from app.models.autofill import AppManagement
    apps = await AppManagement.filter(is_active=True).all()
    print("可用的 API Keys:")
    for app in apps:
        print(f"  - App: {app.app_name}, API Key: {app.api_key}")
    
    if apps:
        return apps[0].api_key
    return None

if __name__ == "__main__":
    api_key = asyncio.run(check_api_keys())
    if api_key:
        print(f"\n使用第一个 API Key: {api_key}")
    else:
        print("\n没有找到可用的 API Key")
