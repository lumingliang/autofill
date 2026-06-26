"""
Agent API V2 - 基于 LangGraph 的多 Agent 系统

支持：
- 非流式/流式对话
- 动态 Agent 注册
- 子 Agent 调度
- 全链路 Trace 查询
"""
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.log import logger
from app.schemas.base import Fail, Success
from app.services.agent import (
    AgentSpec,
    chat,
    chat_stream,
    get_agent_factory,
    get_agent_registry,
    todo_manager,
)
from app.services.agent.trace import get_trace_logger

router = APIRouter()


class AgentChatRequest(BaseModel):
    """Agent 对话请求"""

    query: str = Field(..., description="用户输入")
    agent_name: str = Field(default="default", description="Agent 名称")
    session_id: Optional[str] = Field(None, description="会话ID（不传则创建新会话）")
    user_id: Optional[str] = Field("default", description="用户标识")
    inputs: Optional[Dict[str, Any]] = Field(None, description="输入参数")
    stream: bool = Field(True, description="是否流式返回")
    max_iterations: int = Field(20, description="最大迭代次数", ge=1, le=100)


class AgentChatResponse(BaseModel):
    """Agent 对话响应"""

    answer: str = Field("", description="Agent 回答")
    session_id: str = Field("", description="会话ID")
    agent_name: str = Field("", description="Agent 名称")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="执行的工具调用")
    todo_list: List[Dict[str, Any]] = Field(default_factory=list, description="TODO列表")
    finish_reason: str = Field("stop", description="结束原因: stop/error/max_iterations/loop_detected")
    trace_id: Optional[str] = Field(None, description="Trace ID")


class RegisterAgentRequest(BaseModel):
    """动态注册 Agent 请求"""

    spec: AgentSpec


# ==================== 对话 ====================


@router.post("/agent/v2/chat", summary="Agent 对话接口")
async def agent_chat(request: AgentChatRequest, http_request: Request):
    """Agent 对话接口 - 支持自动工具调用、子 Agent 调度和多轮对话"""
    session_id = request.session_id or f"sess_{datetime.now().timestamp()}"

    logger.info({
        "event": "agent_chat_v2_start",
        "agent_name": request.agent_name,
        "session_id": session_id,
        "user_id": request.user_id,
        "stream": request.stream,
        "query": request.query[:200] if request.query else "",
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
                },
            )
        else:
            result = await chat(
                agent_name=request.agent_name,
                query=request.query,
                session_id=session_id,
                user_id=request.user_id,
                inputs=request.inputs,
                max_iterations=request.max_iterations,
            )

            # 同时返回当前 TODO 列表
            result["todo_list"] = todo_manager.get_todos(session_id)

            logger.info({
                "event": "agent_chat_v2_complete",
                "agent_name": request.agent_name,
                "session_id": session_id,
                "finish_reason": result.get("finish_reason", "stop"),
                "tool_calls_count": len(result.get("tool_calls", [])),
                "trace_id": result.get("trace_id"),
                "answer_preview": result.get("answer", "")[:200],
            })

            return Success(data=result)

    except Exception as e:
        error_detail = traceback.format_exc()
        logger.error({
            "event": "agent_chat_v2_error",
            "agent_name": request.agent_name,
            "session_id": session_id,
            "error": str(e),
            "traceback": error_detail,
        })
        return Fail(msg=f"Agent 对话失败: {str(e)}")


# ==================== 会话管理 ====================


@router.post("/agent/v2/clear", summary="清空会话")
async def agent_clear_conversation(session_id: str):
    """清空指定会话，释放主 Agent 运行时并清理所有子 Agent"""
    try:
        factory = get_agent_factory()
        runtime = factory.get_by_session(session_id)
        if runtime is None:
            todo_manager.clear_todos(session_id)
            return Success(data={"session_id": session_id, "status": "no_runtime"})

        runtime.terminate()
        factory.remove_by_session(session_id)
        todo_manager.clear_todos(session_id)
        return Success(
            data={
                "session_id": session_id,
                "agent_name": runtime.spec.name,
                "status": "cleared",
            }
        )
    except Exception as e:
        return Fail(msg=f"清空会话失败: {str(e)}")


@router.get("/agent/v2/todos", summary="获取 TODO 列表")
async def agent_get_todos(session_id: str):
    """获取指定会话的 TODO 列表"""
    try:
        todos = todo_manager.get_todos(session_id)
        return Success(data={"session_id": session_id, "todos": todos})
    except Exception as e:
        return Fail(msg=f"获取 TODO 失败: {str(e)}")


# ==================== Agent 管理 ====================


@router.get("/agent/v2/agents", summary="列出所有 Agent")
async def list_agents():
    """列出当前已注册的所有 Agent"""
    try:
        agents = get_agent_registry().list_agents()
        return Success(data={"agents": [a.model_dump(exclude={"api_key", "base_url"}) for a in agents]})
    except Exception as e:
        return Fail(msg=f"列出 Agent 失败: {str(e)}")


@router.get("/agent/v2/agents/{name}", summary="获取 Agent 详情")
async def get_agent(name: str):
    """获取指定 Agent 规格"""
    try:
        spec = get_agent_registry().get(name)
        return Success(data={"agent": spec.model_dump(exclude={"api_key", "base_url"})})
    except KeyError:
        return Fail(msg=f"Agent '{name}' 不存在")
    except Exception as e:
        return Fail(msg=f"获取 Agent 失败: {str(e)}")


@router.post("/agent/v2/agents", summary="动态注册 Agent")
async def register_agent(request: RegisterAgentRequest):
    """动态注册一个 Agent 规格"""
    try:
        get_agent_registry().register(request.spec)
        return Success(data={"agent_name": request.spec.name, "status": "registered"})
    except Exception as e:
        return Fail(msg=f"注册 Agent 失败: {str(e)}")


@router.delete("/agent/v2/agents/{name}", summary="注销 Agent")
async def unregister_agent(name: str):
    """注销指定 Agent 规格"""
    try:
        ok = get_agent_registry().unregister(name)
        if not ok:
            return Fail(msg=f"Agent '{name}' 不存在")
        return Success(data={"agent_name": name, "status": "unregistered"})
    except Exception as e:
        return Fail(msg=f"注销 Agent 失败: {str(e)}")


@router.get("/agent/v2/agents/{name}/tools", summary="获取 Agent 工具视图")
async def get_agent_tools(name: str):
    """获取指定 Agent 的私有工具视图"""
    try:
        from app.services.agent.tool_registry import get_tool_registry

        spec = get_agent_registry().get(name)
        tools = get_tool_registry().build_agent_tools(spec)
        return Success(
            data={
                "agent_name": name,
                "tools": [
                    {"name": t.name, "description": t.description[:200]} for t in tools
                ],
            }
        )
    except KeyError:
        return Fail(msg=f"Agent '{name}' 不存在")
    except Exception as e:
        return Fail(msg=f"获取工具视图失败: {str(e)}")


# ==================== Trace ====================


@router.get("/agent/v2/traces/{trace_id}", summary="获取 Trace 摘要")
async def get_trace(trace_id: str):
    """获取 Trace 摘要信息"""
    try:
        trace = get_trace_logger().get_trace(trace_id)
        if trace is None:
            return Fail(msg=f"Trace '{trace_id}' 不存在")
        return Success(data=trace)
    except Exception as e:
        return Fail(msg=f"获取 Trace 失败: {str(e)}")


@router.get("/agent/v2/traces/{trace_id}/steps", summary="获取 Trace 步骤")
async def get_trace_steps(trace_id: str):
    """获取 Trace 完整步骤列表"""
    try:
        steps = get_trace_logger().get_steps(trace_id)
        return Success(data={"trace_id": trace_id, "steps": steps})
    except Exception as e:
        return Fail(msg=f"获取 Trace 步骤失败: {str(e)}")
