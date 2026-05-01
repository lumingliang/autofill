#!/usr/bin/env python3
"""检查数据库中菜单的图标配置"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
project_root = '/Users/lu/code/code/py/autofill'
sys.path.insert(0, project_root)
os.chdir(project_root)

from app.settings.config import settings

async def check_menu_icons():
    from tortoise import Tortoise
    from app.models import Menu

    # 构造数据库 URL
    db_url = f"mysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"

    await Tortoise.init(
        db_url=db_url,
        modules={'models': ['app.models']}
    )

    print("=" * 80)
    print("数据库中的菜单图标配置")
    print("=" * 80)

    menus = await Menu.all().order_by('parent_id', 'order')

    for menu in menus:
        parent_name = ""
        if menu.parent_id:
            parent = await Menu.filter(id=menu.parent_id).first()
            if parent:
                parent_name = f" (父菜单: {parent.name})"

        icon_value = menu.icon if menu.icon else "(无图标)"
        menu_type = "目录" if menu.menu_type == "catalog" else "菜单" if menu.menu_type == "menu" else menu.menu_type

        print(f"\n【{menu.name}】{parent_name}")
        print(f"   类型: {menu_type}")
        print(f"   图标: {icon_value}")
        print(f"   路径: {menu.path}")

    await Tortoise.close_connections()
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(check_menu_icons())
