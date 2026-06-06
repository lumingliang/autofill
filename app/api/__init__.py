from fastapi import APIRouter

from .open import open_router
from .v1 import v1_router

# 内部 API (JWT 认证) - 挂载到 /api/v1
internal_router = APIRouter()
internal_router.include_router(v1_router)

# 开放 API (API Key 认证) - 挂载到 /api/v1/open
open_api_router = APIRouter()
open_api_router.include_router(open_router)


__all__ = ["internal_router", "open_api_router"]
