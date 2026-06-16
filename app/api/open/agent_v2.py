"""
Agent API V2 - 基于 1.json 规范的 Agent 接口

支持：
- 非流式对话
- 流式对话（SSE）
- 多轮对话
- 工具调用
"""
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.schemas.base import Fail, Success

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
    conversation_id: Optional[str] = Field(None, description="对话ID")
    user_id: Optional[str] = Field("default", description="用户标识")
    inputs: Optional[Dict[str, Any]] = Field(None, description="输入参数")
    stream: bool = Field(True, description="是否流式返回")
    max_iterations: int = Field(10, description="最大迭代次数", ge=1, le=50)


class AgentChatResponse(BaseModel):
    """Agent 对话响应"""
    answer: str = Field("", description="Agent 回答")
    conversation_id: str = Field("", description="对话ID")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="执行的工具调用")
    todo_list: List[Dict[str, Any]] = Field(default_factory=list, description="TODO列表")
    finish_reason: str = Field("stop", description="结束原因: stop/tool_calls/error/max_iterations")


# ==================== API 路由 ====================

@router.post("/agent/v2/chat", summary="Agent 对话接口")
async def agent_chat_v2(request: AgentChatRequest):
    """
    Agent 对话接口 - 支持自动工具调用和多轮对话
    
    请求参数:
    - query: 用户输入内容
    - conversation_id: 对话ID（可选，不传则创建新对话）
    - user_id: 用户标识
    - inputs: 输入参数
    - stream: 是否流式返回
    - max_iterations: 最大迭代次数
    """
    try:
        from app.services.agent.agent_core import get_agent
        
        agent = get_agent()
        
        # 生成对话ID
        conversation_id = request.conversation_id or f"conv_{datetime.now().timestamp()}"
        
        if request.stream:
            # 流式响应
            async def event_generator():
                async for event in agent.chat_stream(
                    query=request.query,
                    conversation_id=conversation_id,
                    user_id=request.user_id,
                    inputs=request.inputs,
                ):
                    yield event
            
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Conversation-Id": conversation_id,
                }
            )
        else:
            # 非流式响应
            result = await agent.chat(
                query=request.query,
                conversation_id=conversation_id,
                user_id=request.user_id,
                inputs=request.inputs,
            )
            
            return Success(data=result)
            
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Agent Error: {error_detail}")
        return Fail(msg=f"Agent 对话失败: {str(e)}")


@router.post("/agent/v2/clear", summary="清空对话历史")
async def agent_clear_conversation(conversation_id: str):
    """清空指定对话的历史记录"""
    try:
        from app.services.agent.agent_core import get_agent
        
        agent = get_agent()
        agent.conversation_manager.clear(conversation_id)
        
        return Success(data={"conversation_id": conversation_id, "status": "cleared"})
    except Exception as e:
        return Fail(msg=f"清空对话失败: {str(e)}")


@router.get("/agent/v2/todos", summary="获取 TODO 列表")
async def agent_get_todos(conversation_id: str):
    """获取指定对话的 TODO 列表"""
    try:
        from app.services.agent.tool_executor import todo_manager
        
        todos = todo_manager.get_todos(conversation_id)
        return Success(data={"conversation_id": conversation_id, "todos": todos})
    except Exception as e:
        return Fail(msg=f"获取 TODO 失败: {str(e)}")
