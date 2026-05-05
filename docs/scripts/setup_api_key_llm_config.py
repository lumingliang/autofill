#!/usr/bin/env python3
"""
为 API Key 设置默认 LLM 配置
"""

import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from tortoise import Tortoise

from app.models.autofill import AppManagement
from app.models.llm_config import LLMConfig

# 数据库配置
DB_CONFIG = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.mysql",
            "credentials": {
                "host": "127.0.0.1",
                "port": 3306,
                "user": "root",
                "password": "root123456",
                "database": "autofill",
            }
        }
    },
    "apps": {
        "models": {
            "models": [
                "app.models.admin",
                "app.models.autofill",
                "app.models.llm_config",
                "aerich.models",
            ],
            "default_connection": "default",
        }
    },
}


async def setup_llm_config():
    """设置 LLM 配置"""
    await Tortoise.init(config=DB_CONFIG)

    api_key = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"

    # 查找应用
    app = await AppManagement.filter(api_key=api_key, is_active=True).first()
    if not app:
        print(f"❌ 未找到 API Key 对应的应用")
        await Tortoise.close_connections()
        return

    print(f"✅ 找到应用:")
    print(f"   - App Name: {app.app_name}")
    print(f"   - Tenant ID: {app.tenant_id}")

    # 查找魔搭社区配置
    config = await LLMConfig.filter(model_provider="modelscope").first()

    if config:
        print(f"\n✅ 找到魔搭社区配置:")
        print(f"   - Config ID: {config.id}")
        print(f"   - Config Name: {config.name}")
        print(f"   - Model: {config.model_name}")
        print(f"   - Is Default: {config.is_default}")
        print(f"   - Tenant ID: {config.tenant_id}")

        # 检查是否已经是默认配置
        if not config.is_default:
            print(f"\n📝 将此配置设为默认...")
            config.is_default = True
            await config.save()
            print(f"✅ 已设为默认配置")

        # 检查是否属于该租户或者是全局配置
        if config.tenant_id is None:
            print(f"\n✅ 这是全局配置，所有租户都可以使用")
        elif config.tenant_id == app.tenant_id:
            print(f"\n✅ 这是该租户的专用配置")
        else:
            print(f"\n⚠️  配置属于其他租户，需要创建新的配置")
    else:
        print(f"\n❌ 未找到魔搭社区配置，需要创建")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(setup_llm_config())
