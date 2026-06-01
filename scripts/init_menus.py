#!/usr/bin/env python3
"""
菜单初始化脚本

用于手动初始化菜单配置到数据库

使用方法:
    cd /Users/lu/code/code/py/autofill
    python scripts/init_menus.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.init_app import init_menus, init_db
from app.log import logger


async def main():
    """初始化菜单"""
    try:
        logger.info("=" * 60)
        logger.info("开始初始化菜单...")
        logger.info("=" * 60)

        # 初始化数据库连接
        await init_db()
        logger.info("[1/2] 数据库连接已初始化")

        # 初始化菜单
        await init_menus()
        logger.info("[2/2] 菜单已同步到数据库")

        logger.info("=" * 60)
        logger.info("菜单初始化完成！")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"菜单初始化失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
