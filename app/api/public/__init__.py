"""
公开 API 模块 (API Key 认证)

本目录下的接口都使用 API Key 进行认证，不依赖 JWT，
主要供 Dify、三方应用和外部系统调用。
"""

from fastapi import APIRouter

from .autofill import autofill_public_router
from .llm_proxy import llm_proxy_public_router
from .agents import agents_router
from .agent_v2 import agent_v2_router
from .byd_dealer import byd_dealer_public_router
from .test_exception import router as test_exception_router

public_router = APIRouter()

# 智能填单公开接口
public_router.include_router(autofill_public_router)

# LLM 代理公开接口
public_router.include_router(llm_proxy_public_router)

# Agent 统一接口 (V1)
public_router.include_router(agents_router)

# DataQueryAgent V2 接口
public_router.include_router(agent_v2_router)

# 比亚迪经销商门店公开接口
public_router.include_router(byd_dealer_public_router)

# 异常测试接口（仅用于开发和测试环境）
public_router.include_router(test_exception_router)

__all__ = ["public_router"]
