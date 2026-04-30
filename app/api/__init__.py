from fastapi import APIRouter

from .autofill_public import autofill_public_router
from .v1 import v1_router

api_router = APIRouter()
api_router.include_router(v1_router, prefix="/v1")

# 公开接口 (Dify/三方应用调用，使用 API Key 认证)
api_router.include_router(autofill_public_router)


__all__ = ["api_router"]
