"""
MCP 系统提示词段落动态生成器

根据 .trae/mcp.json 中配置的 schema 路径，扫描工具描述文件，
生成 <mcp_file_system> 段落供系统提示词使用。

如果本地 schema 目录不存在或为空，会尝试通过 SSE 连接 MCP server，
调用 tools/list 获取工具列表并缓存到本地 schema 目录。
"""
import asyncio
import json
import os
from typing import Any, Dict, List, Optional

import httpx

from app.log import logger
from app.settings.config import settings


async def _call_mcp_method(
    server_url: str,
    method: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """通过 SSE 传输调用单个 MCP JSON-RPC 方法并返回 result。"""
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
            init_response = await asyncio.wait_for(init_future, timeout=10.0)
            if init_response.get("error"):
                raise RuntimeError(f"MCP initialize failed: {init_response['error']}")

            # initialized 通知
            await client.post(
                endpoint,
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            )

            # 实际方法调用
            call_id = 2
            call_future: asyncio.Future = asyncio.get_running_loop().create_future()
            pending[call_id] = call_future
            await client.post(
                endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": call_id,
                    "method": method,
                    "params": params or {},
                },
            )
            response = await asyncio.wait_for(call_future, timeout=timeout)
            return response.get("result") or {}
        finally:
            reader_task.cancel()
            try:
                await reader_task
            except asyncio.CancelledError:
                pass


async def _ensure_server_schema(server_url: str, schema_dir_abs: str) -> List[str]:
    """从 MCP server 拉取 tools/list 并缓存到本地 schema 目录。

    返回工具名列表。
    """
    try:
        result = await _call_mcp_method(server_url, "tools/list", timeout=30.0)
    except Exception as exc:
        logger.warning({"event": "mcp_fetch_tools_failed", "url": server_url, "error": str(exc)})
        return []

    tools = result.get("tools", [])
    if not tools:
        return []

    # 如果 schema_dir_abs 是损坏的符号链接，先移除它
    if os.path.islink(schema_dir_abs) and not os.path.exists(schema_dir_abs):
        os.unlink(schema_dir_abs)

    tools_dir = os.path.join(schema_dir_abs, "tools")
    os.makedirs(tools_dir, exist_ok=True)

    names: List[str] = []
    for tool in tools:
        name = tool.get("name")
        if not name:
            continue
        names.append(name)
        schema_path = os.path.join(tools_dir, f"{name}.json")
        try:
            with open(schema_path, "w", encoding="utf-8") as f:
                json.dump(tool, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning({"event": "mcp_schema_write_failed", "path": schema_path, "error": str(exc)})

    logger.info({"event": "mcp_schema_cached", "url": server_url, "schema_dir": schema_dir_abs, "tools": names})
    return names


def _load_mcp_config() -> Dict[str, Any]:
    """加载 .trae/mcp.json 配置。"""
    mcp_json_path = os.path.abspath(
        os.path.join(settings.BASE_DIR, settings.AGENT_BASE_DIR, "mcp.json")
    )
    if not os.path.isfile(mcp_json_path):
        return {}
    try:
        with open(mcp_json_path, "r", encoding="utf-8") as f:
            return json.load(f).get("mcpServers", {}) or {}
    except Exception as exc:
        logger.warning({"event": "mcp_config_load_failed", "path": mcp_json_path, "error": str(exc)})
        return {}


def _resolve_mcp_server_name(server_name: str, servers: Dict[str, Any]) -> Optional[str]:
    """将 system-prompt 风格的 server_name 解析为 mcp.json 中的 key。"""
    if server_name in servers:
        return server_name
    if server_name.startswith("mcp_"):
        short_name = server_name[4:]
        if short_name in servers:
            return short_name
    return None


def _scan_tool_names(schema_dir: str) -> List[str]:
    """扫描 schema 目录下的 tools/*.json 文件，返回工具名列表。"""
    tools_dir = os.path.join(schema_dir, "tools")
    if not os.path.isdir(tools_dir):
        return []
    names = []
    for entry in sorted(os.listdir(tools_dir)):
        if entry.endswith(".json"):
            names.append(entry[:-5])
    return names


def _to_public_server_name(mcp_key: str) -> str:
    """将 mcp.json 中的 key 转换为对外暴露的 server_name。"""
    if not mcp_key.startswith("mcp_"):
        return f"mcp_{mcp_key}"
    return mcp_key


async def build_mcp_section(enabled_servers: Optional[List[str]] = None) -> str:
    """根据启用的 MCP 服务器列表生成 <mcp_file_system> 段落。"""
    servers = _load_mcp_config()
    if not servers:
        return (
            "<mcp_file_system>\n"
            "You have access to MCP (Model Context Protocol) tools through the MCP FileSystem.\n"
            "\n"
            "## MCP Tool Access\n"
            "No MCP servers are currently configured.\n"
            "</mcp_file_system>"
        )

    enabled = enabled_servers or []
    # 未显式配置时默认启用所有服务器
    target_keys = enabled if enabled else list(servers.keys())

    server_blocks: List[str] = []
    for server_name in target_keys:
        mcp_key = _resolve_mcp_server_name(server_name, servers)
        if mcp_key is None:
            continue
        cfg = servers[mcp_key]
        schema_dir = cfg.get("schemaDir", "")
        if not schema_dir:
            continue
        schema_dir_abs = os.path.abspath(os.path.join(settings.BASE_DIR, schema_dir))

        tool_names = _scan_tool_names(schema_dir_abs)
        if not tool_names:
            # 本地 schema 不存在或为空，尝试从 MCP server 动态拉取并缓存
            server_url = cfg.get("url")
            if server_url:
                try:
                    tool_names = await _ensure_server_schema(server_url, schema_dir_abs)
                except Exception as exc:
                    logger.warning(
                        {"event": "mcp_schema_fetch_failed", "server": mcp_key, "error": str(exc)}
                    )
        if not tool_names:
            continue

        public_name = _to_public_server_name(mcp_key)
        server_blocks.append(
            f'<mcp_file_system_server\n'
            f'  name="{public_name}"\n'
            f'  folderPath="{schema_dir_abs}"\n'
            f'  tools="{",".join(tool_names)}"\n'
            f'\n'
            f'>{public_name}</mcp_file_system_server>'
        )

    if not server_blocks:
        return (
            "<mcp_file_system>\n"
            "You have access to MCP (Model Context Protocol) tools through the MCP FileSystem.\n"
            "\n"
            "## MCP Tool Access\n"
            "No MCP servers are currently enabled.\n"
            "</mcp_file_system>"
        )

    servers_xml = "\n\n".join(server_blocks)
    return (
        "<mcp_file_system>\n"
        "You have access to MCP (Model Context Protocol) tools through the MCP FileSystem.\n"
        "\n"
        "## MCP Tool Access\n"
        "The schema of the available MCP tools are stored in the local file system grouped by MCP servers. "
        "You can use the `LS` and `Read` tools to view more detailed MCP tool information to help fully satisfy the user’s request if needed.\n"
        "Each enabled MCP server has its own folder containing JSON descriptor files "
        "(for example, <mcp_info_folder>/<server>/tools/<tool-name>.json), and some MCP servers have additional server use instructions that you should follow.\n"
        "Available MCP servers:\n"
        "<mcp_file_system_servers>\n"
        "\n"
        f"{servers_xml}\n"
        "\n"
        "</mcp_file_system_servers>\n"
        "You can use `run_mcp` tool to call any MCP tool from the above enabled MCP servers. To use MCP tools effectively:\n"
        "1. Discover Available Tools: Browse the MCP tool descriptors in the file system to understand what tools are available. "
        "Each enabled MCP server's tools are stored as JSON descriptor files that contain the tool's parameters and functionality.\n"
        "2. MANDATORY - Always Check Tool Schema First: You MUST ALWAYS list and read the tool's schema/descriptor file BEFORE calling any the MCP tool. "
        "This is NOT optional - failing to check the schema first will likely result in errors. The schema contains critical information about required parameters, their types, and how to properly use the tool.\n"
        "3. IMPORTANT: When calling MCP tools via run_mcp, all tool-specific parameters must be passed inside the `args` field as a JSON object. "
        "Do NOT pass tool parameters as top-level fields - only `server_name`, `tool_name`, and `args` are valid top-level fields for run_mcp.\n"
        "</mcp_file_system>"
    )
