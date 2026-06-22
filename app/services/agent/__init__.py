"""
Agent 服务模块

基于配置化架构实现的 Agent 系统
"""
from app.services.agent.agent_config import AgentConfig
from app.services.agent.agent_factory import (
    AgentFactory,
    chat,
    chat_stream,
    get_agent_factory,
    get_agent_runtime,
    get_agent_runtime_by_session,
    get_agent_runtimes_by_agent,
    get_agent_runtimes_by_tenant,
)
from app.services.agent.agent_loop import AgentLoop, ToolContext
from app.services.agent.agent_registry import AgentRegistry, get_agent_registry
from app.services.agent.agent_runtime import AgentRuntime
from app.services.agent.command_manager import CommandManager, command_manager
from app.services.agent.conversation_manager import ConversationManager
from app.services.agent.prompt_renderer import PromptRenderer, get_prompt_renderer
from app.services.agent.skill_loader import get_skill_prompt, list_skills, load_skill
from app.services.agent.skill_manager import SkillManager, skill_manager
from app.services.agent.todo_manager import TodoManager, todo_manager
from app.services.agent.tool_executor import format_tool_result, format_todo_write_result
from app.services.agent.tool_registry import ToolRegistry, get_tool_registry

__all__ = [
    "AgentConfig",
    "AgentFactory",
    "AgentLoop",
    "AgentRegistry",
    "AgentRuntime",
    "CommandManager",
    "ConversationManager",
    "PromptRenderer",
    "SkillManager",
    "TodoManager",
    "ToolContext",
    "ToolRegistry",
    "chat",
    "chat_stream",
    "command_manager",
    "format_tool_result",
    "format_todo_write_result",
    "get_agent_factory",
    "get_agent_registry",
    "get_agent_runtime",
    "get_agent_runtime_by_session",
    "get_agent_runtimes_by_agent",
    "get_agent_runtimes_by_tenant",
    "get_prompt_renderer",
    "get_skill_prompt",
    "get_tool_registry",
    "list_skills",
    "load_skill",
    "skill_manager",
    "todo_manager",
]
