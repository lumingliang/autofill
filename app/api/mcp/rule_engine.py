"""
规则引擎 MCP API

职责：
- 定义 FastMCP server 的 tools，暴露给 MCP 客户端
- 调用 app.services.mcp.rule_engine_mcp_service 执行业务逻辑
- 不直接操作数据库或 seekdb，不初始化 Tortoise ORM
- 返回 mcp.sse_app() 供主应用在 /mcp/rule_engine 路径挂载

设计原则：
- MCP server 层保持薄，只负责协议适配和参数透传
- 业务逻辑下沉到 service 层，可被 HTTP API、内部服务等多种入口复用
"""
import json
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from app.services.mcp.rule_engine_mcp_service import rule_engine_mcp_service


mcp = FastMCP(
    "rule_engine",
    instructions=(
        "规则引擎数据操纵 MCP 服务器。提供按规则名和字段条件对规则数据进行 "
        "select/update/delete 操作的能力，select 默认返回去重后的结果。"
    ),
)


@mcp.tool()
async def rule_engine_manipulate(
    rule_name: str,
    op: str,
    filters: Dict[str, Any],
    update_values: Optional[Dict[str, Any]] = None,
    distinct: bool = True,
    fields: Optional[List[str]] = None,
) -> str:
    """
    对规则引擎数据进行查询、更新或删除操作。

    Args:
        rule_name: 规则名称，用于定位 seekdb 集合。
        op: 操作类型，可选 "select"、"update"、"delete"。
        filters: 字段过滤条件，例如 {"field_name": "xxx", "field_name2": "yyy"}。
        update_values: 更新操作时的字段值，仅在 op="update" 时有效。
        distinct: select 操作是否对结果去重，默认 True。
        fields: select 操作时返回的字段列表，用于字段投影和按指定字段去重。
                例如查询一级事件类型时传入 ["level1_label", "level1_instruction"]。

    Returns:
        JSON 字符串，包含操作结果或错误信息。
    """
    result = await rule_engine_mcp_service.manipulate(
        rule_name=rule_name,
        op=op,
        filters=filters,
        update_values=update_values,
        distinct=distinct,
        fields=fields,
    )
    return json.dumps(result, ensure_ascii=False)


def get_sse_app():
    """返回可挂载到 FastAPI 主应用的 SSE ASGI 应用。"""
    return mcp.sse_app()
