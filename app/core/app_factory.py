"""
FastAPI 子应用工厂

创建独立的内部 API 和 Open API 子应用，各自拥有独立的中间件和日志分流
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.log import set_app_type
from app.settings import settings

from .middlewares import (
    BackGroundTaskMiddleware,
    HttpAuditLogMiddleware,
    RequestIdMiddleware,
    RequestLoggingMiddleware,
    TenantContextMiddleware,
)
from .open_api_auth import OpenAPIAuthMiddleware


class SetAppTypeMiddleware(BaseHTTPMiddleware):
    """设置应用类型中间件 - 用于日志分流"""

    def __init__(self, app, app_type: str):
        super().__init__(app)
        self.app_type = app_type

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        set_app_type(self.app_type)
        return await call_next(request)


def _add_cors_middleware(app: FastAPI):
    """添加 CORS 中间件"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )


def create_internal_app() -> FastAPI:
    """
    创建内部 API 子应用 (JWT 认证)
    路径: /api/v1/*
    
    Swagger UI: /api/v1/docs
    OpenAPI JSON: /api/v1/openapi.json
    """
    app = FastAPI(
        title="Internal API",
        description="内部管理接口 - JWT 认证",
        version="1.0.0",
        docs_url="/docs",  # 子应用内路径: /api/v1/docs
        openapi_url="/openapi.json",  # 子应用内路径: /api/v1/openapi.json
        redoc_url=None,
    )

    # 添加 CORS 中间件（最外层）
    _add_cors_middleware(app)

    # 添加中间件（按顺序，最先添加的在最外层）
    # 注意：FastAPI 中间件是倒序执行的，最后添加的会包裹在最外层
    app.add_middleware(
        HttpAuditLogMiddleware,
        methods=["GET", "POST", "PUT", "DELETE"],
        exclude_paths=[
            "/base/access_token",
            "/docs",
            "/openapi.json",
        ],
    )
    app.add_middleware(BackGroundTaskMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(TenantContextMiddleware)  # JWT 认证中间件
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(SetAppTypeMiddleware, app_type="internal")

    return app


def create_open_app() -> FastAPI:
    """
    创建 Open API 子应用 (API Key 认证)
    路径: /api/v1/open/*
    
    Swagger UI: /api/v1/open/docs
    OpenAPI JSON: /api/v1/open/openapi.json
    """
    app = FastAPI(
        title="Open API",
        description="开放接口 - API Key 认证",
        version="1.0.0",
        docs_url="/docs",  # 子应用内路径: /api/v1/open/docs
        openapi_url="/openapi.json",  # 子应用内路径: /api/v1/open/openapi.json
        redoc_url=None,
    )

    # 添加 CORS 中间件（最外层）
    _add_cors_middleware(app)

    # 添加中间件（简化版，只有 API Key 认证）
    # 注意：FastAPI 中间件是倒序执行的，最后添加的会包裹在最外层
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(OpenAPIAuthMiddleware)  # API Key 认证中间件
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(SetAppTypeMiddleware, app_type="open")

    return app
