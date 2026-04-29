#!/usr/bin/env python3
"""
调试菜单树结构，模拟前端获取的数据格式
"""

import asyncio
import sys
import json

sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.models.admin import Menu, Role, RoleMenu, User
from app.core.relation import RelationQuery
from tortoise import Tortoise
from app.settings.config import settings


async def init_tortoise():
    await Tortoise.init(config=settings.TORTOISE_ORM)


async def close_tortoise():
    await Tortoise.close_connections()


async def get_all_parent_menus(menu_ids: set) -> set:
    """递归获取所有父菜单ID"""
    all_menu_ids = set(menu_ids)
    current_ids = menu_ids

    while current_ids:
        parent_menus = await Menu.filter(id__in=current_ids).all()
        new_parent_ids = set()
        for menu in parent_menus:
            if menu.parent_id > 0 and menu.parent_id not in all_menu_ids:
                new_parent_ids.add(menu.parent_id)

        if not new_parent_ids:
            break

        all_menu_ids.update(new_parent_ids)
        current_ids = new_parent_ids

    return all_menu_ids


async def debug_menu_tree():
    """调试菜单树结构"""
    await init_tortoise()

    try:
        print("=" * 80)
        print("菜单树调试")
        print("=" * 80)

        # 获取管理员用户
        admin_user = await User.filter(id=1).first()
        if not admin_user:
            print("未找到管理员用户")
            return

        print(f"\n管理员用户: {admin_user.username}")
        print(f"是否超级管理员: {admin_user.is_superuser}")
        print(f"当前租户ID: {admin_user.current_tenant_id}")

        # 模拟后端逻辑
        if admin_user.is_superuser:
            menus = await Menu.all()
            print(f"\n超级管理员获取所有菜单: {len(menus)} 个")
        else:
            menu_ids = await RelationQuery.get_user_menu_ids(admin_user.id, admin_user.current_tenant_id)
            print(f"\n非超级管理员获取菜单ID: {menu_ids}")
            all_menu_ids = await get_all_parent_menus(set(menu_ids))
            menus = await Menu.filter(id__in=all_menu_ids).all()

        # 显示所有菜单详情
        print("\n菜单详情:")
        print("-" * 80)
        for menu in sorted(menus, key=lambda x: x.id):
            print(f"ID: {menu.id:2} | 名称: {menu.name:12} | 路径: {menu.path:20} | "
                  f"类型: {menu.menu_type.value:8} | 父ID: {menu.parent_id:2} | "
                  f"排序: {menu.order}")

        # 构建菜单树（模拟后端逻辑）
        menu_map = {menu.id: {
            "id": menu.id,
            "name": menu.name,
            "path": menu.path,
            "menu_type": menu.menu_type.value,
            "icon": menu.icon,
            "order": menu.order,
            "parent_id": menu.parent_id,
            "component": menu.component,
            "is_hidden": menu.is_hidden,
            "keepalive": menu.keepalive,
            "redirect": menu.redirect,
        } for menu in menus}

        # 找到所有根菜单
        root_menus = []
        for menu in menus:
            if menu.parent_id == 0:
                root_menus.append(menu_map[menu.id])

        print(f"\n根菜单数量: {len(root_menus)}")

        # 递归构建子菜单树
        def build_menu_tree(parent_id: int) -> list:
            children = []
            for menu in menus:
                if menu.parent_id == parent_id:
                    menu_dict = menu_map[menu.id]
                    menu_dict["children"] = build_menu_tree(menu.id)
                    children.append(menu_dict)
            children.sort(key=lambda x: x.get("order", 0))
            return children

        # 为每个根菜单构建树
        res = []
        for root_menu in root_menus:
            root_menu["children"] = build_menu_tree(root_menu["id"])
            res.append(root_menu)

        res.sort(key=lambda x: x.get("order", 0))

        # 输出最终的菜单树
        print("\n" + "=" * 80)
        print("最终的菜单树结构（简化）:")
        print("=" * 80)

        def print_tree(menus, level=0):
            for menu in menus:
                indent = "  " * level
                children_count = len(menu.get("children", []))
                print(f"{indent}└─ {menu['name']} (ID:{menu['id']}, 类型:{menu['menu_type']}, 子菜单:{children_count})")
                if menu.get("children"):
                    print_tree(menu["children"], level + 1)

        print_tree(res)

        # 完整JSON
        print("\n" + "=" * 80)
        print("完整JSON格式:")
        print("=" * 80)
        print(json.dumps(res, ensure_ascii=False, indent=2))

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_tortoise()


if __name__ == "__main__":
    asyncio.run(debug_menu_tree())
