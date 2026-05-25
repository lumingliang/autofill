import json
from typing import Any, Optional
import redis.asyncio as redis
from app.settings import settings


class RedisClient:
    """Redis 客户端单例类 - 增强版"""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def init(self):
        """初始化 Redis 连接 - 使用连接池"""
        if self._client is None:
            pool = redis.ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                db=settings.REDIS_DB,
                decode_responses=True,
                max_connections=20,
                encoding="utf-8"
            )
            self._client = redis.Redis(connection_pool=pool)
        return self._client
    
    async def get_json(self, key: str) -> Any:
        """获取 JSON 数据"""
        data = await self.client.get(self.key(key))
        return json.loads(data) if data else None
    
    async def set_json(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置 JSON 数据"""
        data = json.dumps(value, ensure_ascii=False)
        if ttl:
            await self.client.setex(self.key(key), ttl, data)
        else:
            await self.client.set(self.key(key), data)
    
    async def delete(self, key: str):
        """删除指定的 key"""
        await self.client.delete(self.key(key))

    async def delete_pattern(self, pattern: str):
        """批量删除匹配的 key"""
        keys = await self.client.keys(self.key(pattern))
        if keys:
            await self.client.delete(*keys)
    
    @property
    def client(self):
        """获取 Redis 客户端实例"""
        if self._client is None:
            raise RuntimeError("Redis client not initialized. Call init() first.")
        return self._client
    
    def key(self, name: str) -> str:
        """生成带前缀的 key"""
        return f"{settings.REDIS_KEY_PREFIX}:{name}"
    
    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.close()
            self._client = None


# 全局实例
redis_client = RedisClient()


async def get_redis():
    """获取 Redis 客户端 (用于依赖注入)"""
    return redis_client.client

