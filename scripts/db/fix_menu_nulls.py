#!/usr/bin/env python3
"""
修复菜单表的 NULL 值
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.settings.config import settings
from tortoise import Tortoise


async def fix_menu_nulls():
    """修复菜单表的 NULL 值"""
    await Tortoise.init(config=settings.TORTOISE_ORM)
    conn = Tortoise.get_connection("mysql")

    fixes = [
        ("menu", "path", "''"),
        ("menu", "component", "''"),
        ("menu", "icon", "''"),
        ("menu", "redirect", "''"),
        ("menu", "menu_type", "'catalog'"),
        ("menu", "remark", "'{}'"),
    ]

    print("开始修复菜单表 NULL 值...")

    for table, column, default_value in fixes:
        try:
            sql = f"UPDATE `{table}` SET `{column}` = {default_value} WHERE `{column}` IS NULL"
            await conn.execute_script(sql)
            print(f"✅ 修复 {table}.{column}")
        except Exception as e:
            print(f"⚠️  {table}.{column}: {e}")

    print("\n菜单表 NULL 值修复完成！")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(fix_menu_nulls())
