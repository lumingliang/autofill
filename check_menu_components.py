#!/usr/bin/env python3
"""
检查菜单 component 字段
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


async def check_components():
    """检查所有菜单的 component 字段"""
    await init_tortoise()

    try:
        print("=" * 80)
        print("菜单 component 字段检查")
        print("=" * 80)

        all_menus = await Menu.all().order_by("id")

        print(f"\n共 {len(all_menus)} 个菜单:\n")
        print(f"{'ID':<5} {'名称':<15} {'类型':<10} {'component':<30} {'是否有前导/':<12}")
        print("-" * 80)

        for menu in all_menus:
            has_slash = "是" if (menu.component and menu.component.startswith("/")) else "否"
            component = menu.component or "(空)"
            print(f"{menu.id:<5} {menu.name:<15} {menu.menu_type.value:<10} {component:<30} {has_slash:<12}")

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_tortoise()


if __name__ == "__main__":
    asyncio.run(check_components())
