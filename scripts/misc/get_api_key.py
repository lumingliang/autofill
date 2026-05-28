#!/usr/bin/env python3
"""
获取应用的 API Key

使用方法:
    python get_api_key.py [--app-name APP_NAME]

示例:
    python get_api_key.py
    python get_api_key.py --app-name test_app
"""

import argparse
import asyncio
import sys

# 添加项目路径
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from tortoise import Tortoise
from app.settings.config import settings


async def init_db():
    """初始化数据库连接"""
    await Tortoise.init(
        db_url=f"mysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}",
        modules={'models': ['app.models.autofill', 'app.models.admin']}
    )


async def get_api_key(app_name: str = None):
    """获取应用的 API Key"""
    from app.models.autofill import AppManagement

    try:
        if app_name:
            app = await AppManagement.filter(app_name=app_name).first()
            if app:
                print(f"应用名称: {app.app_name}")
                print(f"API Key: {app.api_key}")
                return app.api_key
            else:
                print(f"未找到应用: {app_name}")
                return None
        else:
            # 获取所有应用
            apps = await AppManagement.filter(is_active=True).all()
            if not apps:
                print("未找到任何应用")
                return None

            print("可用的应用和 API Key:")
            print("-" * 80)
            for app in apps:
                print(f"应用名称: {app.app_name}")
                print(f"API Key: {app.api_key}")
                print(f"租户ID: {app.tenant_id}")
                print("-" * 80)
            return apps[0].api_key if apps else None
    except Exception as e:
        print(f"查询失败: {e}")
        return None


async def main_async():
    parser = argparse.ArgumentParser(description="获取应用的 API Key")
    parser.add_argument("--app-name", help="应用名称（可选，不指定则列出所有）")

    args = parser.parse_args()

    # 初始化数据库
    await init_db()

    try:
        api_key = await get_api_key(args.app_name)

        if api_key:
            print(f"\n使用 API Key: {api_key}")
            return 0
        return 1
    finally:
        await Tortoise.close_connections()


def main():
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
