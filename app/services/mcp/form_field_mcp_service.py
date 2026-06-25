"""
表单字段 MCP 业务服务

职责：
- 对接 test_server/mock_api_server.py（端口 6666）提供的表单字段接口
- 封装字段列表、级联选项、模板内容、表单提交等业务操作
- 不处理 MCP 协议细节，返回可序列化的业务结果
"""
import os
from typing import Any, Dict, List, Optional

import httpx

from app.log import logger


MOCK_API_BASE_URL = os.environ.get("AUTOFILL_MOCK_API_URL", "http://localhost:6666")


class FormFieldMCPService:
    """表单字段 MCP 业务服务"""

    def __init__(self, base_url: str = MOCK_API_BASE_URL):
        self.base_url = base_url.rstrip("/")

    async def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """发送 HTTP 请求并解析响应。"""
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error("表单字段 MCP 请求失败", url=url, method=method, error=str(e))
            return {"success": False, "error": f"请求失败: {e}"}

    async def get_form_fields(self) -> Dict[str, Any]:
        """获取表单字段列表。"""
        result = await self._request("GET", "/api/form/fields")
        if result.get("code") != 200:
            return {"success": False, "error": result.get("msg", "获取字段列表失败")}
        return {"success": True, "fields": result.get("data", [])}

    async def get_field_options(
        self,
        field_id: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取字段选项（级联字段需传入 parent_id）。"""
        params = {}
        if parent_id:
            params["parent_id"] = parent_id
        result = await self._request("GET", f"/api/form/fields/{field_id}/options", params=params)
        if result.get("code") != 200:
            return {"success": False, "error": result.get("msg", "获取选项失败")}
        return {"success": True, "field_id": field_id, "options": result.get("data", {}).get("options", [])}

    async def get_template(self, level3_event_type_id: str) -> Dict[str, Any]:
        """根据三级事件类型 ID 获取服务记录模板。"""
        result = await self._request("GET", f"/api/templates/{level3_event_type_id}")
        if result.get("code") != 200:
            return {"success": False, "error": result.get("msg", "获取模板失败")}
        return {"success": True, "template": result.get("data", {})}

    async def submit_form(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提交表单。"""
        result = await self._request("POST", "/api/form/submit", json={"data": data})
        if result.get("code") != 200:
            return {"success": False, "error": result.get("msg", "提交失败")}
        return {"success": True, "result": result.get("data", {})}


# 全局服务实例
form_field_mcp_service = FormFieldMCPService()
