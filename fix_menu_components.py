#!/usr/bin/env python3
"""
修复菜单 component 字段，移除前导斜杠
"""

import asyncio
import sys

sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.models.admin import Menu
from tortoise import Tortoise
from app.settings.config import settings


async def init_tortoise():
    await Tortoise.init(config=settings.TORTOISE_ORM)


async def close_tortoise():
    await Tortoise.close_connections()


async def fix_menu_components():
    """修复所有菜单的 component 字段"""
    await init_tortoise()

    try:
        print("=" * 60)
        print("修复菜单 component 字段")
        print("=" * 60)

        all_menus = await Menu.all()
        fixed_count = 0

        for menu in all_menus:
            if menu.component and menu.component.startswith("/"):
                old_component = menu.component
                menu.component = menu.component.lstrip("/")
                await menu.save()
                fixed_count += 1
                print(f"  修复: {menu.name:15} | {old_component:25} -> {menu.component}")

        print(f"\n✅ 共修复 {fixed_count} 个菜单")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_tortoise()


if __name__ == "__main__":
    asyncio.run(fix_menu_components())
