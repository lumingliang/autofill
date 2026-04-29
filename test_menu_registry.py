#!/usr/bin/env python3
"""
测试菜单注册中心功能
"""

import asyncio
import sys

sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.core.menu_registry import MenuConfig, menu_registry
from app.core.menu_config import register_all_menus
from app.schemas.menus import MenuType
from tortoise import Tortoise
from app.settings.config import settings


async def init_tortoise():
    """初始化数据库连接"""
    await Tortoise.init(config=settings.TORTOISE_ORM)


async def close_tortoise():
    """关闭数据库连接"""
    await Tortoise.close_connections()


async def test_menu_registry():
    """测试菜单注册中心"""
    await init_tortoise()

    try:
        print("=" * 60)
        print("测试菜单注册中心")
        print("=" * 60)

        # 清空之前的注册
        menu_registry.clear()

        # 注册所有菜单
        print("\n1. 注册所有菜单配置...")
        register_all_menus()
        print("   ✓ 菜单注册完成")

        # 同步到数据库
        print("\n2. 同步菜单到数据库...")
        await menu_registry.sync_to_database()
        print("   ✓ 菜单同步完成")

        # 验证数据库中的菜单
        print("\n3. 验证数据库中的菜单...")
        from app.models.admin import Menu

        all_menus = await Menu.all().order_by("order")
        print(f"   数据库中共有 {len(all_menus)} 个菜单:")

        for menu in all_menus:
            parent_info = f" (父ID: {menu.parent_id})" if menu.parent_id > 0 else ""
            print(f"   - {menu.name:15} | {menu.path:20} | {menu.menu_type.value}{parent_info}")

        print("\n" + "=" * 60)
        print("✅ 菜单注册中心测试通过！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_tortoise()


async def test_incremental_sync():
    """测试增量同步功能"""
    await init_tortoise()

    try:
        print("\n" + "=" * 60)
        print("测试增量同步功能")
        print("=" * 60)

        # 清空之前的注册
        menu_registry.clear()

        # 注册原始菜单
        print("\n1. 注册原始菜单...")
        register_all_menus()
        await menu_registry.sync_to_database()

        # 模拟新增一个菜单
        print("\n2. 模拟新增菜单...")
        new_menus = [
            MenuConfig(
                name="测试菜单",
                path="/test",
                menu_type=MenuType.CATALOG,
                icon="material-symbols:test",
                order=99,
                redirect="/test/page",
                children=[
                    MenuConfig(
                        name="测试页面",
                        path="page",
                        menu_type=MenuType.MENU,
                        icon="material-symbols:page",
                        order=1,
                        component="/test/page",
                    ),
                ],
            ),
        ]
        menu_registry.register(new_menus)

        # 再次同步
        print("\n3. 再次同步（应该只新增测试菜单）...")
        await menu_registry.sync_to_database()

        # 验证
        from app.models.admin import Menu
        test_menu = await Menu.filter(name="测试菜单").first()
        if test_menu:
            print(f"   ✓ 新菜单已创建: {test_menu.name} (ID: {test_menu.id})")
        else:
            print("   ✗ 新菜单未找到")

        # 清理测试数据
        print("\n4. 清理测试数据...")
        await Menu.filter(name__in=["测试菜单", "测试页面"]).delete()
        print("   ✓ 测试数据已清理")

        print("\n" + "=" * 60)
        print("✅ 增量同步测试通过！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_tortoise()


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_menu_registry())
    asyncio.run(test_incremental_sync())
