"""
Redis 客户端模块
提供全局 Redis 连接管理和便捷操作
"""
import redis.asyncio as redis

from app.settings import settings


class RedisClient:
    """Redis 客户端单例类"""

    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def init(self):
        """初始化Redis连接"""
        if self._client is None:
            self._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                db=settings.REDIS_DB,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    @property
    def client(self):
        """获取Redis客户端实例"""
        if self._client is None:
            raise RuntimeError("Redis client not initialized. Call init() first.")
        return self._client

    def key(self, name: str) -> str:
        """生成带前缀的key"""
        return f"{settings.REDIS_KEY_PREFIX}:{name}"

    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.close()
            self._client = None


# 全局实例
redis_client = RedisClient()


async def get_redis():
    """获取Redis客户端 (用于依赖注入)"""
    return redis_client.client
