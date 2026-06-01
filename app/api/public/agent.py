"""
Public Agent 接口 - Dify Agent 转发服务

使用 API Key 认证，不依赖 JWT
根据 api_key 查询对应的 Dify Agent URL，转发请求到 Dify
"""
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.core.dify_agent_auth import DifyAgentAuth
from app.schemas.base import Fail, Success
from app.schemas.dify_agent import AgentChatRequest
from app.services.autofill.dify_agent_service import dify_agent_service

router = APIRouter(tags=["public-agent"])


@router.post("/agent/chat", summary="Agent 对话接口")
async def agent_chat(
    request: AgentChatRequest,
    auth_info: dict = Depends(DifyAgentAuth.authenticate),
):
    """
    Dify Agent 对话接口

    根据 api_key 查询对应的 Dify Agent 配置，转发请求到 Dify
    Header 中携带 Dify 的 API Key

    请求参数:
    - query: 用户输入内容
    - conversation_id: 对话ID（可选，用于保持上下文）
    - user: 用户标识（可选）
    - inputs: 输入参数（可选）
    """
    # 从认证信息中获取 api_key
    api_key = auth_info["api_key"]

    # 查询 Agent 配置
    agent = await dify_agent_service.get_agent_by_api_key(api_key)
    if not agent:
        raise HTTPException(status_code=404, detail="未找到对应的 Agent 配置")

    if not agent.is_active:
        raise HTTPException(status_code=403, detail="Agent 已禁用")

    # 构建 Dify 请求
    dify_payload = {
        "query": request.query,
        "inputs": request.inputs or {},
        "response_mode": "blocking",  # 默认使用阻塞模式
    }

    if request.conversation_id:
        dify_payload["conversation_id"] = request.conversation_id

    if request.user:
        dify_payload["user"] = request.user

    try:
        # 转发请求到 Dify
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                agent.agent_url,
                json=dify_payload,
                headers={
                    "Authorization": f"Bearer {agent.api_key}",
                    "Content-Type": "application/json",
                }
            )
            response.raise_for_status()
            result = response.json()

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
    auth_info: dict = Depends(DifyAgentAuth.authenticate),
):
    """
    Dify Agent 对话流式接口

    根据 api_key 查询对应的 Dify Agent 配置，流式转发请求到 Dify
    """
    # 从认证信息中获取 api_key
    api_key = auth_info["api_key"]

    # 查询 Agent 配置
    agent = await dify_agent_service.get_agent_by_api_key(api_key)
    if not agent:
        raise HTTPException(status_code=404, detail="未找到对应的 Agent 配置")

    if not agent.is_active:
        raise HTTPException(status_code=403, detail="Agent 已禁用")

    # 构建 Dify 请求
    dify_payload = {
        "query": request.query,
        "inputs": request.inputs or {},
        "response_mode": "streaming",  # 流式模式
    }

    if request.conversation_id:
        dify_payload["conversation_id"] = request.conversation_id

    if request.user:
        dify_payload["user"] = request.user

    async def stream_generator():
        """流式响应生成器"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                agent.agent_url,
                json=dify_payload,
                headers={
                    "Authorization": f"Bearer {agent.api_key}",
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
        }
    )
