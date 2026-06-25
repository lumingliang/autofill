"""
RunMCP 工具 - 调用 MCP 工具

使用 langchain MultiServerMCPClient 维护与各个 MCP 服务器的 SSE 连接，
并按 server_name + tool_name 路由调用。
"""
import asyncio
import json
import os
from functools import lru_cache
from typing import Any, Dict, Optional

from langchain_core.tools import BaseTool, StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel, Field

from app.services.agent.tool_executor import format_tool_result
from app.settings.config import settings


@lru_cache(maxsize=1)
def _load_mcp_servers() -> Dict[str, Any]:
    """加载 MCP 服务器配置，支持多个基础目录，按优先级合并（前面的覆盖后面的）。"""
    servers: Dict[str, Any] = {}
    base_dirs = settings.AGENT_BASE_DIR if isinstance(settings.AGENT_BASE_DIR, list) else [settings.AGENT_BASE_DIR]
    # 按优先级从低到高加载，确保高优先级覆盖低优先级
    for base_dir in reversed(base_dirs):
        mcp_json_path = os.path.abspath(os.path.join(settings.BASE_DIR, base_dir, "mcp.json"))
        if not os.path.isfile(mcp_json_path):
            continue
        try:
            with open(mcp_json_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            for name, cfg in config.get("mcpServers", {}).items():
                servers[name] = cfg
        except Exception:
            continue
    return servers


def _resolve_server_config(server_name: str) -> Optional[Dict[str, Any]]:
    """根据 server_name 解析对应的 MCP 服务器配置。

    优先直接匹配，再尝试去掉 'mcp_' 前缀匹配（如 mcp_seekdb -> seekdb）。
    """
    servers = _load_mcp_servers()
    if server_name in servers:
        return servers[server_name]
    if server_name.startswith("mcp_"):
        short_name = server_name[4:]
        if short_name in servers:
            return servers[short_name]
    return None


class _MCPClientManager:
    """维护每个 MCP server 独立的 MultiServerMCPClient，按需初始化并复用连接。

    使用单 server 的 MultiServerMCPClient 实例，避免某个 server 不可用时影响其它 server。
    """

    def __init__(self):
        self._clients: Dict[str, MultiServerMCPClient] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def _get_client(self, server_name: str) -> MultiServerMCPClient:
        """获取或初始化指定 server 的 MultiServerMCPClient。"""
        if server_name not in self._clients:
            async with self._global_lock:
                if server_name not in self._locks:
                    self._locks[server_name] = asyncio.Lock()

        async with self._locks[server_name]:
            if server_name in self._clients:
                return self._clients[server_name]

            cfg = _resolve_server_config(server_name)
            if not cfg:
                raise ValueError(f"MCP server '{server_name}' is not configured.")
            transport = cfg.get("type", "sse")
            url = cfg.get("url")
            if not url:
                raise ValueError(f"MCP server '{server_name}' has no URL configured.")

            if transport == "sse":
                connections = {
                    server_name: {
                        "transport": "sse",
                        "url": url,
                        "timeout": cfg.get("timeout", 60),
                    }
                }
            else:
                raise ValueError(f"Unsupported MCP transport '{transport}' for server '{server_name}'.")

            client = MultiServerMCPClient(connections)
            await client.get_tools()
            self._clients[server_name] = client
            return client

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """在指定 MCP 服务器上调用指定工具。"""
        client = await self._get_client(server_name)
        async with client.session(server_name) as session:
            return await session.call_tool(tool_name, arguments)


# 全局 MCP 客户端管理器
_mcp_client_manager = _MCPClientManager()


class RunMCPInput(BaseModel):
    server_name: str = Field(description="Identifier of the MCP server hosting the tool.")
    tool_name: str = Field(description="Name of the MCP tool to invoke.")
    args: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description=(
            "Arguments to pass to the MCP tool, as described in the tool descriptor. "
            "Make sure all required arguments are provided according to the tool parameter schema."
        ),
    )


async def execute_run_mcp(
    server_name: str,
    tool_name: str,
    args: Optional[Dict[str, Any]] = None,
) -> str:
    """执行 run_mcp 工具"""
    args = args or {}

    server_cfg = _resolve_server_config(server_name)
    if not server_cfg or not server_cfg.get("url"):
        return format_tool_result(
            "error",
            {
                "error": f"MCP server '{server_name}' is not configured. "
                         f"Please add it to {settings.AGENT_BASE_DIR}/mcp.json."
            },
        )

    try:
        result = await _mcp_client_manager.call_tool(server_name, tool_name, args)
    except Exception as exc:
        return format_tool_result(
            "error",
            {
                "error": f"Failed to call MCP tool '{tool_name}' on server '{server_name}': {exc}",
                "server_name": server_name,
                "tool_name": tool_name,
                "args": args,
            },
        )

    if result is None:
        return format_tool_result(
            "error",
            {
                "error": "MCP server returned an unexpected response.",
                "response": result,
            },
        )

    # result 为 mcp.types.CallToolResult 结构
    if getattr(result, "isError", False):
        content = getattr(result, "content", [])
        error_text = ""
        for item in content:
            if getattr(item, "type", None) == "text":
                error_text = getattr(item, "text", "")
                break
        return format_tool_result(
            "error",
            {
                "error": error_text or "MCP tool reported an error.",
                "server_name": server_name,
                "tool_name": tool_name,
                "args": args,
            },
        )

    content = getattr(result, "content", [])
    text = ""
    for item in content:
        if getattr(item, "type", None) == "text":
            text = getattr(item, "text", "")
            break

    try:
        parsed = json.loads(text) if text else {}
    except Exception:
        parsed = None

    if isinstance(parsed, dict):
        return format_tool_result("done", parsed)
    return format_tool_result("done", text, is_json=False)


def get_run_mcp_tool() -> BaseTool:
    return StructuredTool.from_function(
        name="run_mcp",
        description=(
            "Call an MCP tool by server identifier and tool name with arbitrary JSON arguments.\n"
            "\n"
            "\n"
            "IMPORTANT: Always obtain tool descriptor by calling LS and Read tool BEFORE calling this tool to ensure correct parameters.\n"
            "\n"
            "This tool is used to call MCP tools and NOT to get tool descriptors.\n"
        ),
        func=None,
        coroutine=execute_run_mcp,
        args_schema=RunMCPInput,
    )
