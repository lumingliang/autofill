#!/usr/bin/env python3
"""
初始化 LLM 提供商数据和菜单数据
"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from tortoise import Tortoise
from app.models.llm_config import LLMProvider
from app.models.admin import Menu
from app.settings.config import settings


# 默认 LLM 提供商数据
DEFAULT_PROVIDERS = [
    {"value": "openai", "label": "OpenAI", "order": 1},
    {"value": "azure", "label": "Azure OpenAI", "order": 2},
    {"value": "anthropic", "label": "Anthropic", "order": 3},
    {"value": "vertex_ai", "label": "Google Vertex AI", "order": 4},
    {"value": "bedrock", "label": "AWS Bedrock", "order": 5},
    {"value": "ollama", "label": "Ollama", "order": 6},
    {"value": "deepseek", "label": "DeepSeek", "order": 7},
    {"value": "openrouter", "label": "OpenRouter", "order": 8},
    {"value": "qwen", "label": "通义千问", "order": 9},
    {"value": "moonshot", "label": "Moonshot", "order": 10},
    {"value": "zhipuai", "label": "智谱 AI", "order": 11},
]


async def init_providers():
    """初始化 LLM 提供商数据"""
    print("初始化 LLM 提供商数据...")
    for provider_data in DEFAULT_PROVIDERS:
        provider, created = await LLMProvider.get_or_create(
            value=provider_data["value"],
            defaults={
                "label": provider_data["label"],
                "order": provider_data["order"],
                "is_active": True,
            }
        )
        if created:
            print(f"  创建提供商: {provider.label}")
        else:
            print(f"  已存在: {provider.label}")
    print("LLM 提供商数据初始化完成！")


async def init_menus():
    """初始化 LLM 配置菜单"""
    print("\n初始化 LLM 配置菜单...")
    
    # 查找系统管理菜单（parent_id=0 且 name 包含系统）
    system_menu = await Menu.filter(name="系统管理", parent_id=0).first()
    
    if not system_menu:
        print("  错误：未找到系统管理菜单，请先创建系统管理菜单")
        return
    
    print(f"  找到系统管理菜单 (ID: {system_menu.id})")
    
    # 检查 LLM 配置菜单是否已存在
    llm_menu = await Menu.filter(name="LLM配置", parent_id=system_menu.id).first()
    
    if llm_menu:
        print(f"  LLM 配置菜单已存在 (ID: {llm_menu.id})")
        # 确保菜单是启用的
        if llm_menu.is_hidden:
            llm_menu.is_hidden = False
            await llm_menu.save()
            print("  已启用 LLM 配置菜单")
    else:
        # 创建 LLM 配置菜单
        llm_menu = await Menu.create(
            name="LLM配置",
            path="llm_config",
            component="system/llm_config",
            icon="ApiOutlined",
            parent_id=system_menu.id,
            menu_type="menu",
            order=100,
            is_hidden=False,
            keepalive=True,
        )
        print(f"  创建 LLM 配置菜单 (ID: {llm_menu.id})")
    
    print("LLM 配置菜单初始化完成！")


async def main():
    """主函数"""
    print("=" * 50)
    print("开始初始化 LLM 数据")
    print("=" * 50)
    
    # 初始化数据库连接
    db_url = f"mysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
    await Tortoise.init(
        db_url=db_url,
        modules={'models': ['app.models']}
    )
    
    try:
        await init_providers()
        await init_menus()
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await Tortoise.close_connections()
    
    print("\n" + "=" * 50)
    print("初始化完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
