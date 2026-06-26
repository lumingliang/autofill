"""
Agent 服务模块

基于 LangGraph 的多 Agent 系统。
"""
from app.services.agent.factory import (
    AgentFactory,
    chat,
    chat_stream,
    get_agent_factory,
)
from app.services.agent.models import AgentSpec
from app.services.agent.registry import AgentRegistry, get_agent_registry
from app.services.agent.runtime import AgentRuntime
from app.services.agent.tool_executor import format_tool_result, format_todo_write_result
from app.services.agent.tool_registry import ToolRegistry, get_tool_registry
from app.services.agent.todo_manager import TodoManager, todo_manager

__all__ = [
    "AgentFactory",
    "AgentRegistry",
    "AgentRuntime",
    "AgentSpec",
    "ToolRegistry",
    "TodoManager",
    "chat",
    "chat_stream",
    "format_tool_result",
    "format_todo_write_result",
    "get_agent_factory",
    "get_agent_registry",
    "get_tool_registry",
    "todo_manager",
]
