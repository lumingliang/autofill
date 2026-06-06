"""
智能填单系统开放接口
使用 API Key 认证，不依赖 JWT
"""
from fastapi import APIRouter

from .event_type_query import router as event_type_query_router
from .feedback import router as feedback_router
from .fill_data import router as fill_data_router
from .rule_execute import router as rule_execute_router

autofill_open_router = APIRouter()

# 包含各模块路由
autofill_open_router.include_router(feedback_router)
autofill_open_router.include_router(fill_data_router)
autofill_open_router.include_router(rule_execute_router)
autofill_open_router.include_router(event_type_query_router)
