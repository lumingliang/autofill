"""
Curl 命令解析器 - 使用 curl-session 库
"""
import re
import json
from typing import Optional, Dict, List

from curl_session import CurlSession

from .types import ParsedCurl, CurlParseError


class CurlParser:
    """Curl 命令解析器 - 基于 curl-session 库"""

    PLACEHOLDER_PATTERN = re.compile(r'\{\{(\w+)\}\}')

    @classmethod
    def parse(cls, curl_str: str) -> ParsedCurl:
        """
        解析 curl 命令

        Args:
            curl_str: curl 命令字符串

        Returns:
            ParsedCurl: 解析后的 curl 信息

        Raises:
            CurlParseError: 解析失败时抛出
        """
        if not curl_str or not curl_str.strip():
            raise CurlParseError("Curl 命令不能为空")

        # 清理 curl 字符串
        curl_str = curl_str.strip()

        # 使用 curl-session 库解析
        try:
            cs = CurlSession(curl_str)
            parsed = cs._parsed
        except Exception as e:
            raise CurlParseError(f"解析 curl 失败: {e}")

        # 提取占位符字段
        all_text = curl_str
        placeholder_fields = list(set(cls.PLACEHOLDER_PATTERN.findall(all_text)))

        # 解析 body_template
        body_template = None
        if parsed.data:
            try:
                if isinstance(parsed.data, str):
                    body_template = json.loads(parsed.data)
                else:
                    body_template = parsed.data
            except json.JSONDecodeError:
                body_template = {"_raw": parsed.data}

        # 解析 query_params_template
        # curl-session 没有直接提供 query params，需要从 URL 解析
        query_params_template = None
        url = parsed.url
        if "?" in url:
            from urllib.parse import parse_qs, urlparse
            parsed_url = urlparse(url)
            if parsed_url.query:
                query_params_template = parse_qs(parsed_url.query)
                # 将列表转换为单个值（如果有多个值则保留列表）
                for key, value in query_params_template.items():
                    if len(value) == 1:
                        query_params_template[key] = value[0]

        # 从 body_template 中提取参数结构（用于构建 FC 调用的参数）
        param_schema = cls._extract_param_schema(body_template, placeholder_fields)

        return ParsedCurl(
            url=parsed.url,
            method=parsed.method,
            headers=parsed.headers,
            body_template=body_template,
            query_params_template=query_params_template,
            placeholder_fields=placeholder_fields,
            param_schema=param_schema
        )

    @classmethod
    def _extract_param_schema(cls, body_template: Optional[Dict], placeholder_fields: List[str]) -> Optional[Dict]:
        """
        从 body_template 中提取参数结构，用于构建 FC 调用的参数

        例如：
        body_template: {"app_key": "xxx", "query": "{{name}}", "city": "{{city}}"}
        返回: {
            "name": {"type": "string", "description": "query参数的值"},
            "city": {"type": "string", "description": "city参数的值"}
        }
        """
        if not body_template:
            return None

        schema = {}
        for field in placeholder_fields:
            # 在 body_template 中查找包含该占位符的字段
            for key, value in body_template.items():
                if isinstance(value, str) and f"{{{{{field}}}}}" in value:
                    schema[field] = {
                        "type": "string",
                        "description": f"{key}参数的值（从用户输入中提取）",
                        "original_field": key
                    }
                    break

        return schema if schema else None

    @classmethod
    def create_session(cls, curl_str: str) -> CurlSession:
        """
        创建 CurlSession 对象，用于实际发送请求

        Args:
            curl_str: curl 命令字符串

        Returns:
            CurlSession: curl-session 的 Session 对象
        """
        try:
            return CurlSession(curl_str)
        except Exception as e:
            raise CurlParseError(f"创建 CurlSession 失败: {e}")


def parse_curl(curl_str: str) -> ParsedCurl:
    """
    解析 curl 命令的便捷函数

    Args:
        curl_str: curl 命令字符串

    Returns:
        ParsedCurl: 解析后的 curl 信息
    """
    return CurlParser.parse(curl_str)
