import asyncio
from app.models.llm_config import LLMConfig
from app.services.llm.litellm_sync_service import litellm_sync_service
from app.settings.config import settings
from tortoise import Tortoise

async def test_sync():
    await Tortoise.init(config=settings.TORTOISE_ORM)
    
    # 测试同步所有配置
    result = await litellm_sync_service.sync_all_configs()
    print(f"Sync result: {result}")
    
    await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(test_sync())
