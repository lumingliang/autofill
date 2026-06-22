"""
Open Agent 接口 - Dify Agent 转发服务

使用 API Key 认证，不依赖 JWT
根据 api_key 查询对应的 Dify Agent URL，转发请求到 Dify
"""
from typing import Optional

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.ctx import Ctx
from app.schemas.base import Fail, Success

router = APIRouter()


class AgentChatRequest(BaseModel):
    """Agent 对话请求"""
    query: str = Field(..., description="用户输入内容")
    agent_name: str = Field(default="default", description="Agent 名称（本地标识，Dify 转发保留）")
    session_id: Optional[str] = Field(None, description="会话ID（可选，用于保持上下文）")
    user: Optional[str] = Field(None, description="用户标识")
    inputs: Optional[dict] = Field(None, description="输入参数（可选）")


@router.post("/agent/chat", summary="Agent 对话接口")
async def agent_chat(
    request: AgentChatRequest,
    http_request: Request,
):
    """
    Dify Agent 对话接口

    根据 api_key 查询对应的 Dify Agent 配置，转发请求到 Dify
    Header 中携带 Dify 的 API Key

    请求参数:
    - query: 用户输入内容
    - agent_name: Agent 名称（本地标识）
    - session_id: 会话ID（可选，用于保持上下文）
    - user: 用户标识（可选）
    - inputs: 输入参数（可选）
    """
    # 从中间件设置的 state 中获取认证信息（已包含 agent_url 和 dify_api_key）
    auth_info = getattr(http_request.state, "auth_info", {})
    agent_url = auth_info.get("agent_url", "")
    dify_api_key = auth_info.get("dify_api_key", "")
    tenant_id = str(Ctx.get_effective_tenant_id())

    if not agent_url or not dify_api_key:
        return Fail(code=401, msg="无效的 Agent 配置")

    # 构建 Dify 请求
    dify_payload = {
        "query": request.query,
        "inputs": request.inputs or {},
        "response_mode": "blocking",  # 默认使用阻塞模式
    }

    if request.session_id:
        dify_payload["conversation_id"] = request.session_id

    if request.user:
        dify_payload["user"] = request.user

    try:
        # 转发请求到 Dify
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                agent_url,
                json=dify_payload,
                headers={
                    "Authorization": f"Bearer {dify_api_key}",
                    "Content-Type": "application/json",
                }
            )
            response.raise_for_status()
            result = response.json()

        # 统一返回字段名
        if isinstance(result, dict):
            result["agent_name"] = request.agent_name
            result["session_id"] = request.session_id
            result["tenant_id"] = tenant_id

        return Success(data=result)

    except httpx.HTTPStatusError as e:
        return Fail(code=e.response.status_code, msg=f"Dify 请求失败: {e.response.text}")
    except httpx.TimeoutException:
        return Fail(code=504, msg="Dify 请求超时")
    except Exception as e:
        return Fail(code=500, msg=f"请求失败: {str(e)}")


@router.post("/agent/chat/stream", summary="Agent 对话流式接口")
async def agent_chat_stream(
    request: AgentChatRequest,
    http_request: Request,
):
    """
    Dify Agent 对话流式接口

    根据 api_key 查询对应的 Dify Agent 配置，流式转发请求到 Dify
    """
    # 从中间件设置的 state 中获取认证信息（已包含 agent_url 和 dify_api_key）
    auth_info = getattr(http_request.state, "auth_info", {})
    agent_url = auth_info.get("agent_url", "")
    dify_api_key = auth_info.get("dify_api_key", "")
    tenant_id = str(Ctx.get_effective_tenant_id())

    if not agent_url or not dify_api_key:
        return Fail(code=401, msg="无效的 Agent 配置")

    # 构建 Dify 请求
    dify_payload = {
        "query": request.query,
        "inputs": request.inputs or {},
        "response_mode": "streaming",  # 流式模式
    }

    if request.session_id:
        dify_payload["conversation_id"] = request.session_id

    if request.user:
        dify_payload["user"] = request.user

    async def stream_generator():
        """流式响应生成器"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                agent_url,
                json=dify_payload,
                headers={
                    "Authorization": f"Bearer {dify_api_key}",
                    "Content-Type": "application/json",
                }
            ) as response:
                async for chunk in response.aiter_text():
                    yield chunk

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-Id": request.session_id or "",
            "X-Agent-Name": request.agent_name,
            "X-Tenant-Id": tenant_id,
        }
    )
