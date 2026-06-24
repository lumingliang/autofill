"""
Agent API V2 - 基于配置化 Agent 架构的接口

支持：
- 非流式对话
- 流式对话（SSE）
- 多轮对话
- 工具调用
- 多租户隔离
"""
import traceback
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.schemas.base import Fail, Success
from app.services.agent import chat, chat_stream, get_agent_runtime_by_session, todo_manager
from app.log import logger

router = APIRouter()


# ==================== 数据模型 ====================

class ToolCall(BaseModel):
    """工具调用定义"""
    id: str = Field(..., description="工具调用ID")
    name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="工具参数")


class AgentChatRequest(BaseModel):
    """Agent 对话请求"""
    query: str = Field(..., description="用户输入")
    agent_name: str = Field(default="default", description="Agent 名称")
    session_id: Optional[str] = Field(None, description="会话ID（不传则创建新会话）")
    user_id: Optional[str] = Field("default", description="用户标识")
    inputs: Optional[Dict[str, Any]] = Field(None, description="输入参数")
    stream: bool = Field(True, description="是否流式返回")
    max_iterations: int = Field(10, description="最大迭代次数", ge=1, le=50)
    debug: bool = Field(False, description="调试模式：不请求大模型，仅导出请求体")


class AgentChatResponse(BaseModel):
    """Agent 对话响应"""
    answer: str = Field("", description="Agent 回答")
    session_id: str = Field("", description="会话ID")
    agent_name: str = Field("", description="Agent 名称")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="执行的工具调用")
    todo_list: List[Dict[str, Any]] = Field(default_factory=list, description="TODO列表")
    finish_reason: str = Field("stop", description="结束原因: stop/tool_calls/error/max_iterations")


# ==================== API 路由 ====================

@router.post("/agent/v2/chat", summary="Agent 对话接口")
async def agent_chat_v2(request: AgentChatRequest, http_request: Request):
    """
    Agent 对话接口 - 支持自动工具调用和多轮对话

    请求参数:
    - query: 用户输入内容
    - agent_name: Agent 名称（默认 default）
    - session_id: 会话ID（可选，不传则创建新会话）
    - user_id: 用户标识
    - inputs: 输入参数
    - stream: 是否流式返回
    - max_iterations: 最大迭代次数
    """
    session_id = request.session_id or f"sess_{datetime.now().timestamp()}"

    logger.info({
        "event": "agent_chat_start",
        "agent_name": request.agent_name,
        "session_id": session_id,
        "user_id": request.user_id,
        "stream": request.stream,
        "query": request.query[:200] if request.query else ""
    })

    try:
        if request.stream:
            async def event_generator():
                async for event in chat_stream(
                    agent_name=request.agent_name,
                    query=request.query,
                    session_id=session_id,
                    user_id=request.user_id,
                    inputs=request.inputs,
                    max_iterations=request.max_iterations,
                    debug=request.debug,
                ):
                    yield event

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Session-Id": session_id,
                    "X-Agent-Name": request.agent_name,
                }
            )
        else:
            result = await chat(
                agent_name=request.agent_name,
                query=request.query,
                session_id=session_id,
                user_id=request.user_id,
                inputs=request.inputs,
                max_iterations=request.max_iterations,
                debug=request.debug,
            )

            logger.info({
                "event": "agent_chat_complete",
                "agent_name": request.agent_name,
                "session_id": session_id,
                "finish_reason": result.get("finish_reason", "stop"),
                "tool_calls_count": len(result.get("tool_calls", [])),
                "answer_preview": result.get("answer", "")[:200]
            })

            return Success(data=result)

    except Exception as e:
        error_detail = traceback.format_exc()
        logger.error({
            "event": "agent_chat_error",
            "agent_name": request.agent_name,
            "session_id": session_id,
            "error": str(e),
            "traceback": error_detail
        })
        return Fail(msg=f"Agent 对话失败: {str(e)}")


@router.post("/agent/v2/clear", summary="清空对话历史")
async def agent_clear_conversation(session_id: str):
    """清空指定对话的历史记录（按 session_id 唯一标识）"""
    try:
        runtime = get_agent_runtime_by_session(session_id)
        if runtime is None:
            return Success(data={"session_id": session_id, "status": "no_runtime"})

        runtime.conversation_manager.clear()
        return Success(data={"session_id": session_id, "agent_name": runtime.config.name, "status": "cleared"})
    except Exception as e:
        return Fail(msg=f"清空对话失败: {str(e)}")


@router.get("/agent/v2/todos", summary="获取 TODO 列表")
async def agent_get_todos(session_id: str):
    """获取指定会话的 TODO 列表"""
    try:
        todos = todo_manager.get_todos(session_id)

        logger.info({
            "event": "agent_get_todos",
            "session_id": session_id,
            "todos_count": len(todos)
        })

        return Success(data={"session_id": session_id, "todos": todos})
    except Exception as e:
        logger.error({
            "event": "agent_get_todos_error",
            "session_id": session_id,
            "error": str(e)
        })
        return Fail(msg=f"获取 TODO 失败: {str(e)}")
