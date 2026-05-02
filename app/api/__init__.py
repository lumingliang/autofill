from fastapi import APIRouter

from .public import public_router
from .v1 import v1_router

api_router = APIRouter()

# 内部 API (JWT 认证)
api_router.include_router(v1_router, prefix="/v1")

# 公开 API (API Key 认证，供 Dify/三方应用调用)
api_router.include_router(public_router)


__all__ = ["api_router"]
