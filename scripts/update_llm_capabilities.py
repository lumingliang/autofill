#!/usr/bin/env python3
"""
更新 LLM 配置的 capabilities，将所有 structured_output_methods 的 supported 设置为 True
"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from tortoise import Tortoise
from app.models.llm_config import LLMConfig
from app.settings.config import settings


async def init_db():
    """初始化数据库连接"""
    # 构建 MySQL 连接 URL
    db_url = f"mysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
    await Tortoise.init(
        db_url=db_url,
        modules={'models': ['app.models']}
    )


async def update_capabilities():
    """更新所有 LLM 配置的 capabilities"""
    # 获取默认能力配置（所有 supported 为 True）
    default_capabilities = LLMConfig.get_default_capabilities()
    
    # 查询所有 LLM 配置
    configs = await LLMConfig.all()
    
    print(f"找到 {len(configs)} 条 LLM 配置")
    
    updated_count = 0
    for config in configs:
        # 获取当前 capabilities
        current_capabilities = config.capabilities or {}
        
        # 更新 structured_output_methods
        structured_methods = current_capabilities.get("structured_output_methods", {})
        
        # 将所有方法的 supported 设置为 True
        for method_name, method_config in structured_methods.items():
            if isinstance(method_config, dict):
                method_config["supported"] = True
        
        # 确保所有默认方法都存在且 supported 为 True
        for method_name, default_config in default_capabilities["structured_output_methods"].items():
            if method_name not in structured_methods:
                structured_methods[method_name] = default_config.copy()
            else:
                structured_methods[method_name]["supported"] = True
        
        # 更新 capabilities
        current_capabilities["structured_output_methods"] = structured_methods
        config.capabilities = current_capabilities
        
        # 保存
        await config.save()
        updated_count += 1
        print(f"✅ 已更新配置: {config.name} (ID: {config.id})")
    
    print(f"\n✅ 共更新 {updated_count} 条配置")
    print("所有 structured_output_methods 的 supported 已设置为 True")


async def main():
    """主函数"""
    await init_db()
    try:
        await update_capabilities()
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
