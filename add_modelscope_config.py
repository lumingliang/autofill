#!/usr/bin/env python3
"""
通过 API 添加魔搭社区配置
"""

import asyncio
import sys

sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.controllers.llm_config import llm_config_controller
from app.schemas.llm_config import LLMConfigCreate
from tortoise import Tortoise
from app.settings.config import settings


async def init_tortoise():
    await Tortoise.init(config=settings.TORTOISE_ORM)


async def close_tortoise():
    await Tortoise.close_connections()


async def add_modelscope_config():
    """添加魔搭社区配置"""
    await init_tortoise()

    try:
        # 检查是否已存在
        existing = await llm_config_controller.model.filter(
            model_provider="modelscope",
            model_name="Qwen/QwQ-32B"
        ).first()

        if existing:
            print(f"魔搭社区配置已存在 (ID: {existing.id})")
            return

        # 创建配置
        config_data = LLMConfigCreate(
            name="魔搭社区-QwQ-32B",
            model_provider="modelscope",
            model_name="Qwen/QwQ-32B",
            api_key="ms-919b1188-52f3-4654-b3bd-c46ab3bcf738",
            api_base="https://api-inference.modelscope.cn/v1/",
            temperature=0.7,
            max_tokens=2048,
            top_p=1.0,
            is_active=True,
            is_default=False,
            description="魔搭社区ModelScope QwQ-32B模型配置"
        )

        config = await llm_config_controller.create_config(
            obj_in=config_data,
            current_tenant_id=None,
            is_superuser=True
        )

        print(f"✅ 魔搭社区配置添加成功!")
        print(f"   ID: {config.id}")
        print(f"   名称: {config.name}")
        print(f"   提供商: {config.model_provider}")
        print(f"   模型: {config.model_name}")
        print(f"   API Base: {config.api_base}")

    except Exception as e:
        print(f"❌ 添加失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_tortoise()


if __name__ == "__main__":
    asyncio.run(add_modelscope_config())
