"""
RunMCP 工具 - 调用 MCP 工具
"""
import asyncio
import json
import os
from functools import lru_cache
from typing import Any, Dict, Optional

import httpx
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from app.services.agent.tool_executor import format_tool_result
from app.settings.config import settings


@lru_cache(maxsize=1)
def _load_mcp_servers() -> Dict[str, Any]:
    mcp_json_path = os.path.abspath(
        os.path.join(settings.BASE_DIR, settings.AGENT_BASE_DIR, "mcp.json")
    )
    if not os.path.isfile(mcp_json_path):
        return {}
    try:
        with open(mcp_json_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config.get("mcpServers", {}) or {}
    except Exception:
        return {}


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


async def _call_mcp_tool(server_url: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """通过 SSE 传输调用 MCP 工具并返回 JSON-RPC 结果。"""
    base_url = server_url.rstrip("/")
    if base_url.endswith("/sse"):
        base_url = base_url[:-4]

    async with httpx.AsyncClient(timeout=60.0) as client:
        pending: Dict[int, asyncio.Future] = {}
        endpoint_future: asyncio.Future[str] = asyncio.get_running_loop().create_future()

        async def sse_reader() -> None:
            async with client.stream("GET", f"{base_url}/sse") as response:
                event_type: Optional[str] = None
                async for line in response.aiter_lines():
                    if line.startswith("event: "):
                        event_type = line[7:]
                    elif line.startswith("data: "):
                        data_str = line[6:]
                        if event_type == "endpoint" and not endpoint_future.done():
                            ep = data_str
                            if ep.startswith("/"):
                                ep = f"{base_url}{ep}"
                            endpoint_future.set_result(ep)
                        elif event_type == "message":
                            data = json.loads(data_str)
                            msg_id = data.get("id")
                            if isinstance(msg_id, int) and msg_id in pending:
                                pending[msg_id].set_result(data)
                        event_type = None

        reader_task = asyncio.create_task(sse_reader())

        try:
            endpoint = await asyncio.wait_for(endpoint_future, timeout=10.0)

            # initialize 握手
            init_id = 1
            init_future: asyncio.Future = asyncio.get_running_loop().create_future()
            pending[init_id] = init_future
            await client.post(
                endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": init_id,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "autofill-agent", "version": "0.1.0"},
                    },
                },
            )
            await asyncio.wait_for(init_future, timeout=10.0)

            # initialized 通知
            await client.post(
                endpoint,
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            )

            # 工具调用
            call_id = 2
            call_future: asyncio.Future = asyncio.get_running_loop().create_future()
            pending[call_id] = call_future
            await client.post(
                endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": call_id,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                },
            )
            return await asyncio.wait_for(call_future, timeout=30.0)
        finally:
            reader_task.cancel()
            try:
                await reader_task
            except asyncio.CancelledError:
                pass


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

    server_url = server_cfg["url"]

    try:
        response = await _call_mcp_tool(server_url, tool_name, args)
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

    result = response.get("result") if isinstance(response, dict) else None
    if not result:
        return format_tool_result(
            "error",
            {
                "error": "MCP server returned an unexpected response.",
                "response": response,
            },
        )

    if result.get("isError"):
        content = result.get("content", [])
        error_text = ""
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                error_text = item.get("text", "")
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

    content = result.get("content", [])
    text = ""
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            text = item.get("text", "")
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
