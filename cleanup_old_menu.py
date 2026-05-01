#!/usr/bin/env python3
"""
清理旧的 LLM 配置菜单数据
"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from tortoise import Tortoise
from app.models.admin import Menu
from app.settings.config import settings


async def cleanup_old_menu():
    """清理旧的 LLM 配置菜单"""
    print("清理旧的 LLM 配置菜单...")
    
    # 查找系统管理菜单
    system_menu = await Menu.filter(name="系统管理", parent_id=0).first()
    if not system_menu:
        print("  未找到系统管理菜单")
        return
    
    # 查找系统管理下的旧 LLM 配置菜单
    old_llm_menu = await Menu.filter(name="LLM配置", parent_id=system_menu.id).first()
    if old_llm_menu:
        await old_llm_menu.delete()
        print(f"  已删除旧的 LLM 配置菜单 (ID: {old_llm_menu.id})")
    else:
        print("  未找到旧的 LLM 配置菜单")
    
    print("清理完成！")


async def main():
    """主函数"""
    print("=" * 50)
    print("开始清理旧菜单数据")
    print("=" * 50)
    
    # 初始化数据库连接
    db_url = f"mysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
    await Tortoise.init(
        db_url=db_url,
        modules={'models': ['app.models']}
    )
    
    try:
        await cleanup_old_menu()
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await Tortoise.close_connections()
    
    print("\n" + "=" * 50)
    print("清理完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
