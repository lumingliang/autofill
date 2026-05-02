"""
公开 API 模块 (API Key 认证)

本目录下的接口都使用 API Key 进行认证，不依赖 JWT，
主要供 Dify、三方应用和外部系统调用。
"""

from fastapi import APIRouter

from .autofill import autofill_public_router
from .llm_proxy import llm_proxy_public_router
from .query_agent import query_agent_public_router
from .agents import agents_router
from .test_exception import router as test_exception_router

public_router = APIRouter()

# 智能填单公开接口
public_router.include_router(autofill_public_router)

# LLM 代理公开接口
public_router.include_router(llm_proxy_public_router, prefix="/api")

# QueryAgent 公开接口（旧版，保留兼容）
public_router.include_router(query_agent_public_router, prefix="/api")

# Agent 统一接口（新版，推荐使用）
public_router.include_router(agents_router, prefix="/api")

# 异常测试接口（仅用于开发和测试环境）
public_router.include_router(test_exception_router, prefix="/api")

__all__ = ["public_router"]
