"""
LLM 代理公开接口 (API Key 认证)
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, Request
from fastapi.exceptions import HTTPException

from app.controllers.llm_config import llm_config_controller
from app.core.autofill_auth import APIKeyAuth
from app.core.request_parser import parse_request_params
from app.log import logger
from app.schemas.base import Fail, Success
from app.schemas.llm_config import LLMProxyRequest
from app.services.llm_proxy_service import llm_proxy_service

llm_proxy_public_router = APIRouter()


@llm_proxy_public_router.post("/llm/proxy", summary="LLM 结构化输出代理接口")
async def llm_proxy(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    LLM 结构化输出代理接口
    使用 API Key 认证
    """
    try:
        params = await parse_request_params(request, LLMProxyRequest)

        if not params.get("query"):
            return Fail(code=400, msg="query 参数不能为空")
        if not params.get("tools"):
            return Fail(code=400, msg="tools 参数不能为空")

        config = await llm_config_controller.get_default_config(
            tenant_id=auth_info.get("tenant_id", 0),
            app_name=auth_info.get("app_name", None)
        )

        if not config:
            return Fail(code=404, msg="未找到 LLM 配置")

        result = await llm_proxy_service.process_request(
            query=params["query"],
            tools=params["tools"],
            system_prompt=params.get("system_prompt", ""),
            tool_choice=params.get("tool_choice"),
            config=config
        )

        return Success(data=result)

    except ValueError as e:
        logger.error(f"LLM proxy validation error: {e}")
        return Fail(code=400, msg=str(e))
    except Exception as e:
        logger.error(f"LLM proxy error: {e}")
        return Fail(code=500, msg=f"LLM 处理失败: {str(e)}")
