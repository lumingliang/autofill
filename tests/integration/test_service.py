import asyncio
from app.models.llm_config import LLMConfig
from app.services.structured_output import StructuredOutputService
from app.settings.config import settings
from tortoise import Tortoise

async def test_service():
    await Tortoise.init(config=settings.TORTOISE_ORM)
    
    # 获取配置
    config = await LLMConfig.get(id=1)
    print(f"Config: {config.name}")
    print(f"Litellm params: {config.litellm_params}")
    
    # 创建服务
    service = StructuredOutputService(config)
    
    # 测试结构化输出
    tools = [
        {
            "name": "extract_person_info",
            "description": "提取人员信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "姓名"
                    },
                    "age": {
                        "type": "integer",
                        "description": "年龄"
                    },
                    "email": {
                        "type": "string",
                        "description": "邮箱"
                    }
                },
                "required": ["name", "age", "email"]
            }
        }
    ]
    
    result = await service.generate(
        query="请提取以下信息：姓名张三，年龄25岁，邮箱zhangsan@example.com",
        tools=tools,
        system_prompt="你是一个信息提取助手，请从用户输入中提取结构化信息。",
        preferred_methods=["with_structured_output"]
    )
    
    print(f"\nResult success: {result.success}")
    print(f"Result method: {result.method}")
    print(f"Result data: {result.data}")
    print(f"Result error: {result.error}")
    
    await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(test_service())
