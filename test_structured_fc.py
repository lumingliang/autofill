#!/usr/bin/env python3
"""测试 StructuredOutputService 的 function calling"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.core.init_app import init_db
from app.models.llm_config import LLMConfig
from app.services.llm.structured_output import StructuredOutputService

async def test_fc():
    await init_db()
    
    # 获取 DeepSeek-R1-0528 配置
    config = await LLMConfig.get(name="DeepSeek-R1-0528")
    if not config:
        print("❌ 未找到 DeepSeek-R1-0528 配置")
        return
    
    print(f"配置名称: {config.name}")
    print(f"模型名称: {config.litellm_params.get('model', '')}")
    
    # 创建服务实例
    service = StructuredOutputService(config)
    print(f"服务使用的模型名称: {service.model_name}")
    
    # 定义工具
    tools = [{
        "type": "function",
        "function": {
            "name": "search_store",
            "description": "搜索门店信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "门店名称"},
                    "city": {"type": "string", "description": "城市"}
                },
                "required": ["name", "city"]
            }
        }
    }]
    
    query = "帮我找一下重庆的比亚迪门店"
    system_prompt = "你是一个 helpful 助手。当用户需要搜索门店时，请使用 search_store 工具。"
    
    print("\n" + "=" * 80)
    print("测试 custom_fc_non_stream 方法")
    print("=" * 80)
    
    result = await service._method_custom_fc_non_stream(
        query=query,
        tools=tools,
        system_prompt=system_prompt
    )
    
    print(f"\n方法: {result.method}")
    print(f"成功: {result.success}")
    
    if result.success:
        print(f"数据: {result.data}")
    else:
        print(f"错误: {result.error}")
    
    print("\n" + "=" * 80)
    print("测试 generate 方法（自动选择）")
    print("=" * 80)
    
    result2 = await service.generate(
        query=query,
        tools=tools,
        system_prompt=system_prompt
    )
    
    print(f"\n方法: {result2.method}")
    print(f"成功: {result2.success}")
    
    if result2.success:
        print(f"数据: {result2.data}")
    else:
        print(f"错误: {result2.error}")

if __name__ == "__main__":
    asyncio.run(test_fc())
