#!/usr/bin/env python3
"""
检查数据库中的菜单结构和层级
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


async def check_menus():
    await init_tortoise()

    try:
        print("=" * 80)
        print("数据库菜单检查")
        print("=" * 80)

        all_menus = await Menu.all().order_by("order")

        print(f"\n总共有 {len(all_menus)} 个菜单:\n")

        # 构建菜单树
        menu_map = {m.id: m for m in all_menus}
        children_map = {}

        for menu in all_menus:
            if menu.parent_id not in children_map:
                children_map[menu.parent_id] = []
            children_map[menu.parent_id].append(menu)

        # 打印菜单树
        def print_menu_tree(parent_id=0, level=0):
            if parent_id not in children_map:
                return

            for menu in sorted(children_map[parent_id], key=lambda x: x.order):
                indent = "  " * level
                parent_info = f" [父ID: {menu.parent_id}]" if menu.parent_id > 0 else " [根菜单]"
                print(f"{indent}└─ ID:{menu.id:2} | {menu.name:12} | {menu.path:20} | {menu.menu_type.value:8}{parent_info}")
                print_menu_tree(menu.id, level + 1)

        print_menu_tree()

        # 检查问题
        print("\n" + "=" * 80)
        print("问题检查")
        print("=" * 80)

        issues = []

        # 检查1: 子菜单的 parent_id 是否正确
        for menu in all_menus:
            if menu.parent_id > 0:
                parent = menu_map.get(menu.parent_id)
                if not parent:
                    issues.append(f"菜单 '{menu.name}' (ID:{menu.id}) 的父菜单 (ID:{menu.parent_id}) 不存在")

        # 检查2: 目录菜单应该有子菜单或重定向
        for menu in all_menus:
            if menu.menu_type.value == "catalog":
                has_children = menu.id in children_map and len(children_map[menu.id]) > 0
                if not has_children and not menu.redirect:
                    issues.append(f"目录菜单 '{menu.name}' (ID:{menu.id}) 没有子菜单且没有重定向")

        # 检查3: 路径格式
        for menu in all_menus:
            if menu.parent_id == 0:  # 根菜单
                if not menu.path.startswith("/"):
                    issues.append(f"根菜单 '{menu.name}' (ID:{menu.id}) 的路径 '{menu.path}' 应该以 '/' 开头")
            else:  # 子菜单
                if menu.path.startswith("/"):
                    issues.append(f"子菜单 '{menu.name}' (ID:{menu.id}) 的路径 '{menu.path}' 不应该以 '/' 开头")

        if issues:
            print("\n发现以下问题:")
            for issue in issues:
                print(f"  ⚠ {issue}")
        else:
            print("\n✅ 未发现明显问题")

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_tortoise()


if __name__ == "__main__":
    asyncio.run(check_menus())
