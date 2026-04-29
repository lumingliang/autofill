#!/usr/bin/env python3
"""
添加 AI大模型 菜单到数据库
用于升级现有系统
"""

import asyncio
import sys

# 添加项目根目录到路径
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.models.admin import Menu, Role
from app.schemas.menus import MenuType
from app.core.relation import RelationQuery
from tortoise import Tortoise
from app.settings.config import settings


async def init_tortoise():
    """初始化数据库连接"""
    await Tortoise.init(config=settings.TORTOISE_ORM)


async def close_tortoise():
    """关闭数据库连接"""
    await Tortoise.close_connections()


async def add_ai_menu():
    """添加 AI大模型 菜单和 LLM配置 子菜单"""
    await init_tortoise()

    try:
        # 检查 AI大模型 菜单是否已存在
        ai_menu = await Menu.filter(name="AI大模型").first()

        if ai_menu:
            print("✓ AI大模型 菜单已存在，跳过创建")
            ai_menu_id = ai_menu.id
        else:
            # 创建 AI大模型 目录菜单
            ai_menu = await Menu.create(
                menu_type=MenuType.CATALOG,
                name="AI大模型",
                path="/ai",
                order=4,
                parent_id=0,
                icon="material-symbols:psychology-outline",
                is_hidden=False,
                component="Layout",
                keepalive=False,
                redirect="/ai/llm-config",
            )
            ai_menu_id = ai_menu.id
            print(f"✓ 创建 AI大模型 菜单成功，ID: {ai_menu_id}")

        # 检查 LLM配置 子菜单是否已存在
        llm_menu = await Menu.filter(name="LLM配置").first()

        if llm_menu:
            print("✓ LLM配置 子菜单已存在，跳过创建")
            llm_menu_id = llm_menu.id
        else:
            # 创建 LLM配置 子菜单
            llm_menu = await Menu.create(
                menu_type=MenuType.MENU,
                name="LLM配置",
                path="llm-config",
                order=1,
                parent_id=ai_menu_id,
                icon="material-symbols:model-training-outline",
                is_hidden=False,
                component="/ai/llm-config",
                keepalive=False,
            )
            llm_menu_id = llm_menu.id
            print(f"✓ 创建 LLM配置 子菜单成功，ID: {llm_menu_id}")

        # 为管理员角色分配菜单权限
        admin_role = await Role.filter(id=1).first()
        if admin_role:
            # 检查是否已分配权限
            from app.models.admin import RoleMenu

            ai_exists = await RoleMenu.filter(role_id=admin_role.id, menu_id=ai_menu_id).exists()
            if not ai_exists:
                await RelationQuery.batch_add_role_menus([(admin_role.id, ai_menu_id)])
                print(f"✓ 为管理员角色分配 AI大模型 菜单权限成功")
            else:
                print("✓ 管理员角色已有 AI大模型 菜单权限，跳过")

            llm_exists = await RoleMenu.filter(role_id=admin_role.id, menu_id=llm_menu_id).exists()
            if not llm_exists:
                await RelationQuery.batch_add_role_menus([(admin_role.id, llm_menu_id)])
                print(f"✓ 为管理员角色分配 LLM配置 菜单权限成功")
            else:
                print("✓ 管理员角色已有 LLM配置 菜单权限，跳过")
        else:
            print("⚠ 未找到管理员角色（ID=1），跳过权限分配")

        print("\n✅ AI大模型 菜单添加完成！")
        print("请刷新页面查看新菜单")

    except Exception as e:
        print(f"\n❌ 添加菜单失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_tortoise()


if __name__ == "__main__":
    print("=" * 50)
    print("添加 AI大模型 菜单到数据库")
    print("=" * 50)
    asyncio.run(add_ai_menu())
