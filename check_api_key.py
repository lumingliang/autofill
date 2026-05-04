#!/usr/bin/env python3
"""检查数据库中的 API Key"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.core.init_app import init_db
from app.models.autofill import AppManagement

async def check_api_keys():
    # 初始化数据库
    await init_db()

    apps = await AppManagement.filter(is_active=True).all()
    print(f"找到 {len(apps)} 个活跃应用:\n")
    for app in apps:
        print(f"应用名称: {app.app_name}")
        print(f"API Key: {app.api_key}")
        print(f"租户ID: {app.tenant_id}")
        print(f"Dify URL: {app.dify_url}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(check_api_keys())
