import json
from typing import Optional

from fastapi import Header, HTTPException

from app.core.redis import redis_client
from app.models.admin import Tenant
from app.models.autofill import AppManagement


class APIKeyAuth:
    """API Key 认证类（用于 Dify/三方应用调用）"""

    @classmethod
    async def authenticate(cls, authorization: str = Header(..., description="Authorization: Bearer {api_key}")) -> dict:
        """
        解析 Authorization: Bearer {api_key}
        返回: {"tenant_id": int, "app_name": str, "domain": str, "dify_url": str, "dify_api_key": str}
        """
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization format")

        api_key = authorization.replace("Bearer ", "").strip()

        # 1. 尝试从 Redis 缓存获取
        # try:
        #     cache_key = redis_client.key(f"api_key:{api_key}")
        #     cached = await redis_client.client.get(cache_key)
        #     if cached:
        #         return json.loads(cached)
        # except Exception:
        #     # Redis 连接失败时继续查询数据库
        #     pass

        # 2. 查询数据库
        app = await AppManagement.filter(api_key=api_key, is_active=True).first()
        if not app:
            raise HTTPException(status_code=401, detail="Invalid API key")

        # 查询租户域名
        tenant = await Tenant.filter(id=app.tenant_id).first()
        domain = tenant.domain if tenant else ""

        result = {
            "tenant_id": app.tenant_id,
            "app_name": app.app_name,
            "domain": domain,
            "dify_url": app.dify_url,
            "dify_api_key": app.dify_api_key,
        }

        # 3. 写入 Redis 缓存 (1小时)
        try:
            await redis_client.client.setex(cache_key, 3600, json.dumps(result))
        except Exception:
            # Redis 写入失败时忽略
            pass

        return result
