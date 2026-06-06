"""
开放 API 模块 (API Key 认证)

本目录下的接口都使用 API Key 进行认证，不依赖 JWT，
主要供 Dify、三方应用和外部系统调用。
"""

from fastapi import APIRouter

from .agent import router as agent_router
from .autofill import autofill_open_router
from .test_exception import router as test_exception_router

# Open API 主路由，统一使用 "Open API" tag
open_router = APIRouter(tags=["Open API"])

# 智能填单开放接口
open_router.include_router(autofill_open_router)

# Agent 开放接口
open_router.include_router(agent_router)

# 异常测试接口（仅用于开发和测试环境）
open_router.include_router(test_exception_router)

__all__ = ["open_router"]
