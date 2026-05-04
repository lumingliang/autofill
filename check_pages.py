#!/usr/bin/env python3
"""检查数据库中的页面"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.core.init_app import init_db
from app.models.autofill import FillPage

async def check_pages():
    # 初始化数据库
    await init_db()

    pages = await FillPage.filter(is_active=True).all()
    print(f"找到 {len(pages)} 个页面:\n")
    for page in pages:
        print(f"页面名称: {page.page_name}")
        print(f"页面编码: {page.page_code}")
        print(f"应用名称: {page.app_name}")
        print(f"租户ID: {page.tenant_id}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(check_pages())
