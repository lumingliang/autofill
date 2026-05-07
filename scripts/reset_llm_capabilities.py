#!/usr/bin/env python3
"""
重置 LLM 模型的 capabilities 配置
将 C4AI-Command-R-Plus 的结构化输出方法状态重置为默认
"""
import asyncio
import json

# 需要设置 Django/Tortoise 环境
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

# 设置环境变量
import os
os.environ.setdefault('APP_ENV', 'dev')

async def reset_capabilities():
    """重置 C4AI-Command-R-Plus 的 capabilities"""
    from tortoise import Tortoise

    # 数据库配置
    DB_CONFIG = {
        'connections': {
            'default': 'mysql://root:123456@localhost:3306/autofill'
        },
        'apps': {
            'models': {
                'models': ['app.models'],
                'default_connection': 'default',
            }
        }
    }

    # 初始化数据库连接
    await Tortoise.init(config=DB_CONFIG)

    from app.models.llm_config import LLMConfig

    # 获取默认配置
    default_capabilities = LLMConfig.get_default_capabilities()

    # 查找 C4AI-Command-R-Plus 配置
    config = await LLMConfig.filter(name='C4AI-Command-R-Plus').first()

    if config:
        print(f"找到配置: {config.name}")
        print(f"当前 capabilities: {json.dumps(config.capabilities, indent=2, ensure_ascii=False)}")

        # 重置 capabilities
        config.capabilities = default_capabilities
        await config.save()

        print(f"\n已重置为默认 capabilities: {json.dumps(default_capabilities, indent=2, ensure_ascii=False)}")
        print("✅ 重置成功！")
    else:
        print("❌ 未找到 C4AI-Command-R-Plus 配置")

        # 列出所有可用配置
        configs = await LLMConfig.all()
        print(f"\n可用配置列表 ({len(configs)}个):")
        for c in configs:
            print(f"  - {c.name} (默认: {c.is_default}, 启用: {c.is_active})")

    # 关闭数据库连接
    await Tortoise.close_connections()

if __name__ == "__main__":
    print("重置 LLM 模型 capabilities 脚本")
    print("=" * 60)
    asyncio.run(reset_capabilities())
