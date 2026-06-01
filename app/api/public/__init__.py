"""
公开 API 模块 (API Key 认证)

本目录下的接口都使用 API Key 进行认证，不依赖 JWT，
主要供 Dify、三方应用和外部系统调用。
"""

from fastapi import APIRouter

from .agent import router as agent_router
from .autofill import autofill_public_router
from .test_exception import router as test_exception_router

public_router = APIRouter()

# 智能填单公开接口
public_router.include_router(autofill_public_router)

# Agent 公开接口
public_router.include_router(agent_router)

# 异常测试接口（仅用于开发和测试环境）
public_router.include_router(test_exception_router)

__all__ = ["public_router"]
