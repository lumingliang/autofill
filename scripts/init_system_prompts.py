#!/usr/bin/env python3
"""
初始化系统提示词脚本
将 config/system_prompts.json 中的默认提示词导入数据库

使用方法:
    cd /Users/lu/code/code/py/autofill
    python scripts/init_system_prompts.py
"""
import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.system_prompt import SystemPrompt
from app.settings import settings
from tortoise import Tortoise


async def init_tortoise():
    """初始化Tortoise ORM"""
    await Tortoise.init(config=settings.TORTOISE_ORM)


async def close_tortoise():
    """关闭Tortoise ORM连接"""
    await Tortoise.close_connections()


async def init_system_prompts():
    """初始化系统提示词"""
    config_path = Path(__file__).parent.parent / "app" / "config" / "system_prompts.json"
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    created_count = 0
    skipped_count = 0

    print("=" * 60)
    print("开始初始化系统提示词")
    print("=" * 60)

    for prompt_data in config.get("prompts", []):
        # 检查是否已存在（tenant_id=0 全局默认，按name判断）
        exists = await SystemPrompt.filter(
            name=prompt_data["name"],
            tenant_id=0
        ).exists()

        if not exists:
            await SystemPrompt.create(
                name=prompt_data["name"],
                tenant_id=0,
                content=prompt_data["content"],
                category=prompt_data["category"],
                is_default=prompt_data.get("is_default", False),
                is_active=True
            )
            created_count += 1
            print(f"✅ 创建提示词: {prompt_data['name']} [{prompt_data['category']}]")
        else:
            skipped_count += 1
            print(f"⏭️  已存在: {prompt_data['name']} [{prompt_data['category']}]")

    print("=" * 60)
    print(f"完成！新建: {created_count} 个, 跳过: {skipped_count} 个")
    print("=" * 60)


async def main():
    """主函数"""
    try:
        print("正在连接数据库...")
        await init_tortoise()
        print("数据库连接成功！\n")

        await init_system_prompts()

    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await close_tortoise()


if __name__ == "__main__":
    asyncio.run(main())
