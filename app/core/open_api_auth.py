"""
Open API 认证中间件

用于 /api/v1/open/* 路由的 API Key 认证
支持两种认证方式：
1. 普通 Open API - 使用 AppManagement 表
2. Agent API - 使用 DifyAgent 表
"""
import json

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.ctx import Ctx
from app.core.redis import redis_client
from app.log import logger
from app.models.admin import Tenant
from app.models.autofill import AppManagement
from app.models.dify_agent import DifyAgent


class OpenAPIAuthMiddleware(BaseHTTPMiddleware):
    """
    Open API 认证中间件

    处理 Authorization: Bearer {api_key} 认证
    根据路由前缀自动选择认证方式：
    - /api/v1/open/agent/* -> DifyAgent 认证
    - 其他 -> AppManagement 认证
    """

    # Open API 前缀
    OPEN_API_PREFIX: str = "/api/v1/open/"

    # 不需要认证的路径
    EXCLUDE_PATHS: list = [
        "/test/exception",  # 测试异常接口
        "/docs",  # Swagger UI
        "/openapi.json",  # OpenAPI JSON
    ]

    # 使用 AppManagement 认证的路径（覆盖默认的 DifyAgent 认证）
    APP_AUTH_PATHS: list = [
        "/agent/v2",  # Agent V2 使用 AppManagement 认证
    ]

    def _is_open_api(self, path: str) -> bool:
        """检查是否是 Open API 路由"""
        return path.startswith(self.OPEN_API_PREFIX)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        path = request.url.path

        # 如果不是 Open API 路由，直接放行
        if not self._is_open_api(path):
            return await call_next(request)

        # 检查是否在排除列表中
        for exclude_path in self.EXCLUDE_PATHS:
            if exclude_path in path:
                return await call_next(request)

        # 获取 Authorization Header
        authorization = request.headers.get("authorization")
        if not authorization:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "msg": "缺少 Authorization Header", "data": None}
            )

        if not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"code": 401, "msg": "Invalid authorization format, expected: Bearer {api_key}", "data": None}
            )

        api_key = authorization.replace("Bearer ", "").strip()

        # 根据路由前缀选择认证方式
        # 检查是否使用 AppManagement 认证
        for app_path in self.APP_AUTH_PATHS:
            if app_path in path:
                return await self._authenticate_app(request, call_next, api_key)

        if "/agent/" in path:
            # Agent 接口使用 DifyAgent 认证
            return await self._authenticate_agent(request, call_next, api_key)
        else:
            # 普通接口使用 AppManagement 认证
            return await self._authenticate_app(request, call_next, api_key)

    async def _authenticate_app(self, request: Request, call_next: RequestResponseEndpoint, api_key: str):
        """AppManagement 认证（普通 Open API）"""
        try:
            # 1. 尝试从 Redis 缓存获取
            cache_key = redis_client.key(f"api_key:app:{api_key}")
            cached = await redis_client.client.get(cache_key)
            if cached:
                auth_info = json.loads(cached)
                Ctx.set_request_tenant_id(auth_info.get("tenant_id", 0))
                request.state.auth_info = auth_info
                return await call_next(request)
        except Exception:
            pass

        # 2. 查询数据库
        app = await AppManagement.filter(api_key=api_key, is_active=True).first()
        if not app:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "msg": "Invalid API key", "data": None}
            )

        # 查询租户域名
        tenant = await Tenant.filter(id=app.tenant_id).first()
        domain = tenant.domain if tenant else ""

        # 设置租户上下文
        Ctx.set_request_tenant_id(app.tenant_id)

        auth_info = {
            "app_name": app.app_name,
            "domain": domain,
            "tenant_id": app.tenant_id,
            "auth_type": "app",
        }
        request.state.auth_info = auth_info

        # 3. 写入 Redis 缓存 (1小时)
        try:
            cache_key = redis_client.key(f"api_key:app:{api_key}")
            await redis_client.client.setex(cache_key, 3600, json.dumps(auth_info))
        except Exception:
            pass

        return await call_next(request)

    async def _authenticate_agent(self, request: Request, call_next: RequestResponseEndpoint, api_key: str):
        """DifyAgent 认证（Agent 接口）"""
        try:
            # 1. 尝试从 Redis 缓存获取
            cache_key = redis_client.key(f"api_key:agent:{api_key}")
            cached = await redis_client.client.get(cache_key)
            if cached:
                auth_info = json.loads(cached)
                Ctx.set_request_tenant_id(auth_info.get("tenant_id", 0))
                request.state.auth_info = auth_info
                return await call_next(request)
        except Exception:
            pass

        # 2. 查询数据库
        agent = await DifyAgent.filter(api_key=api_key, is_active=True).first()
        if not agent:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "msg": "Invalid API key", "data": None}
            )

        # 设置租户上下文
        Ctx.set_request_tenant_id(agent.tenant_id)

        auth_info = {
            "agent_id": agent.id,
            "agent_name": agent.name,
            "tenant_id": agent.tenant_id,
            "api_key": api_key,
            "agent_url": agent.agent_url,
            "dify_api_key": agent.api_key,
            "auth_type": "agent",
        }
        request.state.auth_info = auth_info

        # 3. 写入 Redis 缓存 (1小时)
        try:
            cache_key = redis_client.key(f"api_key:agent:{api_key}")
            await redis_client.client.setex(cache_key, 3600, json.dumps(auth_info))
        except Exception:
            pass

        return await call_next(request)
