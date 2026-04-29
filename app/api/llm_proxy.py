"""
LLM 代理公开接口
供外部应用（如Dify）调用，使用API Key认证
基于 LangChain + LiteLLM 实现结构化输出
"""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, Request
from fastapi.exceptions import HTTPException

from app.core.autofill_auth import APIKeyAuth
from app.core.request_parser import parse_request_params
from app.schemas.base import Fail, Success
from app.schemas.llm_config import LLMProxyRequest
from app.services.llm_proxy_service import llm_proxy_service

logger = logging.getLogger(__name__)

llm_proxy_router = APIRouter()


async def llm_proxy_handler(
    request: Request,
    auth_info: dict
) -> Dict[str, Any]:
    """
    LLM代理处理逻辑
    """
    # 解析请求参数
    params = await parse_request_params(request, LLMProxyRequest)

    query = params.get("query")
    function_schema = params.get("function_schema")

    if not query:
        return Fail(code=400, msg="缺少query参数")

    if not function_schema:
        return Fail(code=400, msg="缺少function_schema参数")

    # 获取app_key（从auth_info中获取）
    # 这里我们需要从原始请求头中获取Authorization来解析api_key
    authorization = request.headers.get("authorization", "")
    if authorization.startswith("Bearer "):
        app_key = authorization.replace("Bearer ", "").strip()
    else:
        return Fail(code=401, msg="无效的认证信息")

    try:
        # 调用LLM代理服务
        result = await llm_proxy_service.invoke_with_fallback(
            query=query,
            function_schema=function_schema,
            app_key=app_key,
            context=params.get("context"),
        )

        if result["success"]:
            return Success(data=result["data"])
        else:
            return Fail(code=500, msg=result["error"])

    except Exception as e:
        logger.error(f"LLM proxy error: {e}")
        return Fail(code=500, msg=f"LLM调用失败: {str(e)}")


@llm_proxy_router.post("/llm/proxy", summary="LLM结构化输出代理接口")
@llm_proxy_router.get("/llm/proxy", summary="LLM结构化输出代理接口")
async def llm_proxy(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    LLM结构化输出代理接口

    请求参数:
    - query: 用户输入或上下文
    - function_schema: 函数调用参数schema (OpenAI Function Calling格式)
    - context: 可选的额外上下文信息

    示例请求:
    {
        "query": "客户说：我要投诉你们的服务，太糟糕了！",
        "function_schema": {
            "type": "function",
            "function": {
                "name": "classify_scene",
                "description": "根据客服对话内容，识别当前工单所属的业务场景",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "scene_name": {
                            "type": "string",
                            "enum": ["投诉处理", "业务咨询", "预约进店", "道路救援", "配件查询"],
                            "description": "只能从上述选项中选择一个最匹配的场景名称"
                        },
                        "confidence": {
                            "type": "string",
                            "enum": ["高", "中", "低"],
                            "description": "分类置信度，若对话信息模糊可标记为低"
                        }
                    },
                    "required": ["scene_name"]
                }
            }
        }
    }

    认证方式: Authorization: Bearer {api_key}
    """
    return await llm_proxy_handler(request, auth_info)


@llm_proxy_router.post("/llm/proxy/health", summary="LLM代理健康检查")
@llm_proxy_router.get("/llm/proxy/health", summary="LLM代理健康检查")
async def llm_proxy_health(
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    LLM代理健康检查接口
    用于验证API Key和LLM配置是否可用
    """
    from app.controllers.llm_config import llm_config_controller

    # 检查是否有可用的配置
    config = await llm_config_controller.get_default_config(auth_info.get("tenant_id"))

    if not config:
        config = await llm_config_controller.get_default_config(None)

    if not config:
        return Fail(code=503, msg="未找到可用的LLM配置")

    return Success(data={
        "status": "healthy",
        "tenant_id": auth_info.get("tenant_id"),
        "app_name": auth_info.get("app_name"),
        "llm_config": {
            "name": config.name,
            "provider": config.model_provider,
            "model": config.model_name,
        }
    })
