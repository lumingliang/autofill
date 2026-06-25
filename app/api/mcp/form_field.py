"""
表单字段 MCP API

职责：
- 定义 FastMCP server 的 tools，暴露给 MCP 客户端
- 调用 app.services.mcp.form_field_mcp_service 执行业务逻辑
- 不直接访问 mock_api_server.py，只通过 service 层调用
- 返回 mcp.sse_app() 供主应用在 /mcp/form_field 路径挂载
"""
import json
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from app.services.mcp.form_field_mcp_service import form_field_mcp_service


mcp = FastMCP(
    "form_field",
    instructions=(
        "表单字段 MCP 服务器。提供表单字段列表、级联下拉选项、服务记录模板、"
        "表单提交等与自动填单相关的查询能力。"
    ),
)


@mcp.tool()
async def get_form_fields() -> str:
    """获取表单字段列表。"""
    result = await form_field_mcp_service.get_form_fields()
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def get_field_options(field_id: str, parent_id: Optional[str] = None) -> str:
    """
    获取下拉字段选项。

    Args:
        field_id: 字段 ID，如 event_type_level1 / event_type_level2 / event_type_level3。
        parent_id: 父级选项 ID，用于级联查询（如查二级时传一级 ID）。

    Returns:
        JSON 字符串，包含选项列表（label/value）。
    """
    result = await form_field_mcp_service.get_field_options(field_id, parent_id)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def get_template(level3_event_type_id: str) -> str:
    """
    根据三级事件类型 ID 获取服务记录模板。

    Args:
        level3_event_type_id: 三级事件类型 ID，如 EVT001001001。

    Returns:
        JSON 字符串，包含模板内容、模板名称、变量列表等。
    """
    result = await form_field_mcp_service.get_template(level3_event_type_id)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def submit_form(data: Dict[str, Any]) -> str:
    """
    提交表单。

    Args:
        data: 表单数据，必须包含 event_type_level1、event_type_level2、
              event_type_level3、service_summary。

    Returns:
        JSON 字符串，包含提交结果或错误信息。
    """
    result = await form_field_mcp_service.submit_form(data)
    return json.dumps(result, ensure_ascii=False)


def get_sse_app():
    """返回可挂载到 FastAPI 主应用的 SSE ASGI 应用。"""
    return mcp.sse_app()
