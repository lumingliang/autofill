"""
API 执行器
"""
import json
from typing import Any, Dict, Optional

import httpx

from app.log import logger
from ..base.types import APIResult
from ..base.exceptions import APIError
from .curl_parser import ParsedCurl


class APIExecutor:
    """API 执行器"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def execute(
        self,
        parsed: ParsedCurl,
        params: Dict[str, Any]
    ) -> APIResult:
        """
        执行 API 调用

        Args:
            parsed: 解析后的 curl
            params: 参数值

        Returns:
            APIResult: 调用结果
        """
        logger.info(f"[APIExecutor] 开始执行 API: {parsed.method} {parsed.url}")

        try:
            # 构建请求
            url = self._build_url(parsed, params)
            headers = self._build_headers(parsed)
            body = self._build_body(parsed, params)

            # 发送请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=parsed.method,
                    url=url,
                    headers=headers,
                    content=body.encode() if body else None
                )

            # 解析响应
            result_data = self._parse_response(response)

            logger.info(f"[APIExecutor] API 调用完成: {response.status_code}")

            return APIResult(
                success=200 <= response.status_code < 300,
                status_code=response.status_code,
                data=result_data,
                raw_response=response.text
            )

        except httpx.TimeoutException:
            logger.error("[APIExecutor] API 调用超时")
            return APIResult(
                success=False,
                status_code=0,
                error="请求超时"
            )

        except Exception as e:
            logger.error(f"[APIExecutor] API 调用失败: {e}")
            return APIResult(
                success=False,
                status_code=0,
                error=str(e)
            )

    def _build_url(self, parsed: ParsedCurl, params: Dict[str, Any]) -> str:
        """构建 URL"""
        url = parsed.url

        # 添加 query 参数
        query_parts = []
        for key in parsed.query_params.keys():
            if key in params:
                query_parts.append(f"{key}={params[key]}")
            else:
                query_parts.append(f"{key}={parsed.query_params[key]}")

        if query_parts:
            url += "?" + "&".join(query_parts)

        return url

    def _build_headers(self, parsed: ParsedCurl) -> Dict[str, str]:
        """构建 Headers"""
        headers = parsed.headers.copy()

        # 确保有 Content-Type
        if parsed.body and "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        return headers

    def _build_body(self, parsed: ParsedCurl, params: Dict[str, Any]) -> Optional[str]:
        """构建 Body"""
        if not parsed.body_params:
            return None

        body_data = {}
        for key in parsed.body_params.keys():
            # 优先使用 params 中的非空值，否则使用原始值
            if key in params and params[key] not in (None, ""):
                body_data[key] = params[key]
            else:
                body_data[key] = parsed.body_params[key]

        # 根据 content-type 序列化
        content_type = parsed.content_type or "application/json"

        if "json" in content_type.lower():
            return json.dumps(body_data, ensure_ascii=False)

        # Form data
        return "&".join([f"{k}={v}" for k, v in body_data.items()])

    def _parse_response(self, response: httpx.Response) -> Any:
        """解析响应"""
        content_type = response.headers.get("content-type", "")

        # JSON 响应
        if "json" in content_type.lower():
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"_raw": response.text}

        # 尝试解析为 JSON
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"_raw": response.text}
