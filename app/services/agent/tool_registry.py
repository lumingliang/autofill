"""
ToolRegistry - 工具注册表

维护全局工具工厂，并按 AgentSpec 构建 Agent 私有工具视图。
优先复用现有 app/services/agent/tools/ 下的工具实现。
"""
import functools
from typing import Callable, Dict, List, Optional

from langchain_core.tools import BaseTool, StructuredTool

from app.log import logger
from app.services.agent.models import AgentSpec
from app.services.agent.tools import (
    get_ask_user_question_tool,
    get_check_command_status_tool,
    get_delete_file_tool,
    get_glob_tool,
    get_grep_tool,
    get_ls_tool,
    get_read_tool,
    get_run_command_tool,
    get_run_mcp_tool,
    get_search_replace_tool,
    get_skill_tool,
    get_stop_command_tool,
    get_todo_write_tool,
    get_write_tool,
)
from app.services.agent.tools.mcp import RunMCPInput, execute_run_mcp
from app.services.agent.tools.run_agent import get_run_agent_tool


ToolFactory = Callable[..., BaseTool]


# 全局默认工具工厂映射
_DEFAULT_TOOL_FACTORIES: Dict[str, ToolFactory] = {
    "Skill": get_skill_tool,
    "Glob": get_glob_tool,
    "LS": get_ls_tool,
    "Grep": get_grep_tool,
    "Read": get_read_tool,
    "RunCommand": get_run_command_tool,
    "CheckCommandStatus": get_check_command_status_tool,
    "StopCommand": get_stop_command_tool,
    "run_mcp": get_run_mcp_tool,
    "TodoWrite": get_todo_write_tool,
    "SearchReplace": get_search_replace_tool,
    "Write": get_write_tool,
    "DeleteFile": get_delete_file_tool,
    "AskUserQuestion": get_ask_user_question_tool,
}


def _build_run_mcp_for_agent(spec: AgentSpec) -> BaseTool:
    """为指定 Agent 构建带 MCP Server 白名单的 run_mcp 工具"""
    allowed_servers = set(spec.mcp_servers or [])

    async def execute_limited(
        server_name: str,
        tool_name: str,
        args: Optional[Dict] = None,
    ) -> str:
        if allowed_servers and server_name not in allowed_servers:
            from app.services.agent.tool_executor import format_tool_result

            return format_tool_result(
                "error",
                {
                    "error": f"MCP server '{server_name}' is not in the allowed list for agent '{spec.name}'.",
                    "allowed_servers": sorted(allowed_servers),
                },
            )
        return await execute_run_mcp(server_name, tool_name, args or {})

    description = (
        "Call an MCP tool by server identifier and tool name with arbitrary JSON arguments.\n"
        "\n"
        "IMPORTANT: Always obtain tool descriptor by calling LS and Read tool BEFORE calling this tool to ensure correct parameters.\n"
        "\n"
        "This tool is used to call MCP tools and NOT to get tool descriptors.\n"
    )
    if allowed_servers:
        description += f"\nAllowed MCP servers for this agent: {', '.join(sorted(allowed_servers))}\n"

    return StructuredTool.from_function(
        name="run_mcp",
        description=description,
        func=None,
        coroutine=execute_limited,
        args_schema=RunMCPInput,
    )


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._factories: Dict[str, ToolFactory] = dict(_DEFAULT_TOOL_FACTORIES)

    def register(self, name: str, factory: ToolFactory) -> None:
        """注册全局工具工厂"""
        self._factories[name] = factory
        logger.info({"event": "tool_registered", "tool_name": name})

    def unregister(self, name: str) -> bool:
        """注销全局工具工厂"""
        if name in self._factories:
            del self._factories[name]
            logger.info({"event": "tool_unregistered", "tool_name": name})
            return True
        return False

    def list_global(self) -> List[str]:
        """列出所有全局可用工具名"""
        return list(self._factories.keys())

    def has(self, name: str) -> bool:
        """检查工具是否已注册"""
        return name in self._factories

    def build_agent_tools(self, spec: AgentSpec) -> List[BaseTool]:
        """根据 AgentSpec 构建该 Agent 的私有工具视图"""
        tools: List[BaseTool] = []
        for tool_name in spec.toolset:
            if tool_name == "Skill":
                tools.append(get_skill_tool(spec.skills or None))
                continue
            if tool_name == "run_mcp":
                tools.append(_build_run_mcp_for_agent(spec))
                continue
            if tool_name == "run_agent":
                tools.append(get_run_agent_tool())
                continue
            factory = self._factories.get(tool_name)
            if factory is None:
                logger.warning({
                    "event": "tool_not_found",
                    "tool_name": tool_name,
                    "agent_name": spec.name,
                })
                continue
            tools.append(factory())
        return tools


@functools.cache
def get_tool_registry() -> ToolRegistry:
    """获取全局默认 ToolRegistry"""
    return ToolRegistry()
