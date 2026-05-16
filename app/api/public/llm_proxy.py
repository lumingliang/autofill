"""
LLM 代理公开接口 (API Key 认证)
"""
from fastapi import APIRouter, Depends, Request

from app.core.autofill_auth import APIKeyAuth
from app.core.request_parser import parse_request_params
from app.log import logger
from app.schemas.base import Fail, Success
from app.schemas.llm_config import LLMProxyRequest
from app.services.llm.llm_config_service import llm_config_service
from app.services.llm.llm_proxy_service import llm_proxy_service

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

        # 获取默认 LLM 配置
        config = await llm_config_service.get_default_config()

        if not config:
            return Fail(code=400, msg="未找到 LLM 配置")

        result = await llm_proxy_service.process_request(
            query=params["query"],
            tools=params["tools"],
            system_prompt=params.get("system_prompt", ""),
            tool_choice=params.get("tool_choice", "auto"),
            session_id=params.get("session_id"),
            memory_rounds=params.get("memory_rounds") if params.get("memory_rounds") else None,
            config=config
        )

        return Success(data=result)

    except ValueError as e:
        logger.error(f"LLM proxy validation error: {e}")
        return Fail(code=400, msg=str(e))
    except Exception as e:
        logger.error(f"LLM proxy error: {e}")
        return Fail(code=500, msg=f"LLM 处理失败: {str(e)}")
