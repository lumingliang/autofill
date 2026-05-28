"""
智能填单系统公开接口
使用 API Key 认证，不依赖 JWT
"""
from fastapi import APIRouter

from app.api.public.handlers import (
    feedback_router,
    fill_data_router,
    rule_execute_router,
)

autofill_public_router = APIRouter()

# 包含各模块路由
autofill_public_router.include_router(feedback_router)
autofill_public_router.include_router(fill_data_router)
autofill_public_router.include_router(rule_execute_router)
