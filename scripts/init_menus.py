#!/usr/bin/env python3
"""
数据库初始化脚本

用于手动初始化数据库基础数据（菜单、超级管理员等）

使用方法:
    cd /Users/lu/code/code/py/autofill
    
    # 只初始化菜单（默认）
    python scripts/init_menus.py
    
    # 只初始化超级管理员
    python scripts/init_menus.py --superuser
    
    # 初始化所有（菜单 + 超级管理员）
    python scripts/init_menus.py --all
"""

import argparse
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tortoise import Tortoise
from app.core.init_app import init_menus, init_superuser
from app.settings.config import settings
from app.log import logger


async def init_db():
    """初始化数据库连接"""
    await Tortoise.init(config=settings.TORTOISE_ORM)


async def main():
    """初始化数据库数据"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="初始化数据库基础数据")
    parser.add_argument(
        "--superuser",
        action="store_true",
        help="初始化超级管理员",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="初始化所有数据（菜单 + 超级管理员）",
    )
    args = parser.parse_args()

    # 确定要初始化的内容
    init_superuser_flag = args.superuser or args.all
    init_menus_flag = not args.superuser or args.all

    try:
        logger.info("=" * 60)
        logger.info("开始初始化数据库数据...")
        logger.info("=" * 60)

        # 初始化数据库连接
        await init_db()
        logger.info("[✓] 数据库连接已初始化")

        step = 0
        total_steps = (1 if init_superuser_flag else 0) + (1 if init_menus_flag else 0)

        # 初始化超级管理员
        if init_superuser_flag:
            step += 1
            logger.info(f"[{step}/{total_steps}] 开始初始化超级管理员...")
            await init_superuser()
            logger.info(f"[{step}/{total_steps}] 超级管理员初始化完成")

        # 初始化菜单
        if init_menus_flag:
            step += 1
            logger.info(f"[{step}/{total_steps}] 开始初始化菜单...")
            await init_menus()
            logger.info(f"[{step}/{total_steps}] 菜单已同步到数据库")

        logger.info("=" * 60)
        logger.info("数据库初始化完成！")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
