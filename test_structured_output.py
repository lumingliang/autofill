#!/usr/bin/env python3
"""测试 StructuredOutputService 的模型名称处理"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.core.init_app import init_db
from app.models.llm_config import LLMConfig
from app.services.llm.structured_output import StructuredOutputService

async def test_model_name():
    await init_db()
    
    # 获取 DeepSeek-R1-0528 配置
    config = await LLMConfig.get(name="DeepSeek-R1-0528")
    if not config:
        print("❌ 未找到 DeepSeek-R1-0528 配置")
        return
    
    print(f"配置名称: {config.name}")
    print(f"模型提供商: {config.model_provider}")
    print(f"litellm_params: {config.litellm_params}")
    
    # 创建服务实例
    service = StructuredOutputService(config)
    
    print(f"\n原始模型名称: {config.litellm_params.get('model', '')}")
    print(f"处理后模型名称: {service.model_name}")
    
    # 验证模型名称是否正确添加了前缀
    if service.model_name.startswith("openai/"):
        print("\n✅ 模型名称已正确添加 openai/ 前缀")
    else:
        print(f"\n❌ 模型名称缺少 openai/ 前缀: {service.model_name}")

if __name__ == "__main__":
    asyncio.run(test_model_name())
