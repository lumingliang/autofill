"""
Agent 服务模块

基于 1.json 规范实现的 Agent 系统
"""
from app.services.agent.agent_core import TraeAgent, get_agent
from app.services.agent.tool_definitions import get_tool_definitions
from app.services.agent.tool_executor import execute_tool, command_manager, skill_executor
from app.services.agent.system_prompt import get_system_prompt, SYSTEM_PROMPT
from app.services.agent.skill_loader import load_skill, get_skill_prompt, list_skills

__all__ = [
    "TraeAgent",
    "get_agent",
    "get_tool_definitions",
    "execute_tool",
    "command_manager",
    "skill_executor",
    "get_system_prompt",
    "SYSTEM_PROMPT",
    "load_skill",
    "get_skill_prompt",
    "list_skills",
]
