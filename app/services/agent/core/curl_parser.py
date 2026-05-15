"""
Curl 解析器 - 无需占位符，自动从 curl 中提取参数结构
"""
import json
import re
import shlex
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse

from app.log import logger
from ..base.exceptions import ParseError


@dataclass
class ParamSchema:
    """参数 Schema"""
    name: str
    param_type: str = "string"
    description: str = ""
    required: bool = True
    example: Any = None


@dataclass
class ParsedCurl:
    """解析后的 Curl"""
    url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, Any] = field(default_factory=dict)
    body: Optional[str] = None
    body_params: Dict[str, Any] = field(default_factory=dict)
    content_type: Optional[str] = None
    param_schemas: List[ParamSchema] = field(default_factory=list)

    def get_all_params(self) -> Dict[str, Any]:
        """获取所有参数"""
        return {
            **self.query_params,
            **self.body_params
        }


class CurlParser:
    """Curl 解析器"""

    @classmethod
    def parse(cls, curl_command: str) -> ParsedCurl:
        """
        解析 curl 命令，提取参数结构

        Args:
            curl_command: curl 命令字符串

        Returns:
            ParsedCurl: 解析结果
        """
        logger.info("[CurlParser] 开始解析 curl")

        try:
            # 标准化 curl 命令
            curl_command = curl_command.strip()
            if curl_command.startswith("curl "):
                curl_command = curl_command[5:]

            # 解析参数
            tokens = cls._tokenize(curl_command)

            # 提取各个部分
            url = cls._extract_url(tokens)
            method = cls._extract_method(tokens)
            headers = cls._extract_headers(tokens)
            body = cls._extract_body(tokens)
            query_params = cls._extract_query_params(url)

            # 解析 body 参数
            body_params = {}
            content_type = headers.get("Content-Type", "")

            if body:
                body_params = cls._parse_body_params(body, content_type)

            # 构建参数 schema
            param_schemas = cls._build_param_schemas(query_params, body_params)

            parsed = ParsedCurl(
                url=url.split("?")[0],  # 移除 query string
                method=method,
                headers=headers,
                query_params=query_params,
                body=body,
                body_params=body_params,
                content_type=content_type,
                param_schemas=param_schemas
            )

            logger.info(f"[CurlParser] 解析完成: {len(param_schemas)} 个参数")
            return parsed

        except Exception as e:
            logger.error(f"[CurlParser] 解析失败: {e}")
            raise ParseError(f"解析 curl 失败: {e}")

    @classmethod
    def _tokenize(cls, command: str) -> List[str]:
        """分词"""
        try:
            return shlex.split(command)
        except ValueError:
            # 简单分词
            return command.split()

    @classmethod
    def _extract_url(cls, tokens: List[str]) -> str:
        """提取 URL"""
        for i, token in enumerate(tokens):
            if token.startswith("http://") or token.startswith("https://"):
                return token
            if token in ["-X", "--request", "-H", "--header", "-d", "--data", "-b", "--data-binary"]:
                continue
            if i > 0 and tokens[i-1] in ["-X", "--request", "-H", "--header", "-d", "--data", "-b", "--data-binary"]:
                continue
            if token.startswith("http"):
                return token

        raise ParseError("无法从 curl 中提取 URL")

    @classmethod
    def _extract_method(cls, tokens: List[str]) -> str:
        """提取 HTTP 方法"""
        for i, token in enumerate(tokens):
            if token in ["-X", "--request"] and i + 1 < len(tokens):
                return tokens[i + 1].upper()

        # 如果有 body，默认 POST
        if any(t in ["-d", "--data", "-b", "--data-binary"] for t in tokens):
            return "POST"

        return "GET"

    @classmethod
    def _extract_headers(cls, tokens: List[str]) -> Dict[str, str]:
        """提取 Headers"""
        headers = {}

        for i, token in enumerate(tokens):
            if token in ["-H", "--header"] and i + 1 < len(tokens):
                header_str = tokens[i + 1]
                if ":" in header_str:
                    key, value = header_str.split(":", 1)
                    headers[key.strip()] = value.strip()

        return headers

    @classmethod
    def _extract_body(cls, tokens: List[str]) -> Optional[str]:
        """提取 Body"""
        for i, token in enumerate(tokens):
            if token in ["-d", "--data", "-b", "--data-binary"] and i + 1 < len(tokens):
                return tokens[i + 1]

        return None

    @classmethod
    def _extract_query_params(cls, url: str) -> Dict[str, Any]:
        """提取 URL 查询参数"""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        # 转换单值列表为单个值
        result = {}
        for key, values in params.items():
            if len(values) == 1:
                result[key] = cls._infer_type(values[0])
            else:
                result[key] = [cls._infer_type(v) for v in values]

        return result

    @classmethod
    def _parse_body_params(cls, body: str, content_type: str) -> Dict[str, Any]:
        """解析 Body 参数"""
        if not body:
            return {}

        # JSON body
        if "json" in content_type.lower():
            try:
                data = json.loads(body)
                if isinstance(data, dict):
                    return data
                return {"_raw": data}
            except json.JSONDecodeError:
                logger.warning(f"[CurlParser] JSON 解析失败: {body[:100]}")
                return {"_raw": body}

        # Form data
        if "form" in content_type.lower() or "x-www-form-urlencoded" in content_type.lower():
            params = parse_qs(body)
            result = {}
            for key, values in params.items():
                result[key] = values[0] if len(values) == 1 else values
            return result

        # 尝试作为 JSON 解析
        try:
            data = json.loads(body)
            if isinstance(data, dict):
                return data
            return {"_raw": data}
        except json.JSONDecodeError:
            return {"_raw": body}

    @classmethod
    def _build_param_schemas(
        cls,
        query_params: Dict[str, Any],
        body_params: Dict[str, Any]
    ) -> List[ParamSchema]:
        """构建参数 Schema

        包含所有参数，根据值推断参数类型
        有值的参数作为示例，空值或占位符参数需要 Agent 填充
        """
        schemas = []

        def is_placeholder(value: Any) -> bool:
            """检查值是否是占位符，如 {name}, {city} 等"""
            if not isinstance(value, str):
                return False
            return bool(re.match(r'^\{[^}]+\}$', value.strip()))

        # Query 参数
        for key, value in query_params.items():
            needs_fill = value in (None, "", []) or is_placeholder(value)
            schemas.append(ParamSchema(
                name=key,
                param_type=cls._get_type_name(value) if value and not is_placeholder(value) else "string",
                description=f"URL 查询参数: {key}" + (" (需要填充)" if needs_fill else f"，示例: {value}"),
                required=needs_fill,  # 空值或占位符参数需要填充
                example=value if not needs_fill else ""
            ))

        # Body 参数
        for key, value in body_params.items():
            if key == "_raw":
                continue
            needs_fill = value in (None, "", []) or is_placeholder(value)
            schemas.append(ParamSchema(
                name=key,
                param_type=cls._get_type_name(value) if value and not needs_fill else "string",
                description=f"请求体参数: {key}" + (" (需要填充)" if needs_fill else f"，示例: {value}"),
                required=needs_fill,  # 空值或占位符参数需要填充
                example=value if not needs_fill else ""
            ))

        return schemas

    @classmethod
    def _infer_type(cls, value: str) -> Any:
        """推断值类型"""
        # 尝试整数
        try:
            return int(value)
        except ValueError:
            pass

        # 尝试浮点数
        try:
            return float(value)
        except ValueError:
            pass

        # 尝试布尔值
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False

        # 尝试 JSON
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

        # 字符串
        return value

    @classmethod
    def _get_type_name(cls, value: Any) -> str:
        """获取类型名称"""
        type_map = {
            int: "integer",
            float: "number",
            bool: "boolean",
            str: "string",
            list: "array",
            dict: "object"
        }
        return type_map.get(type(value), "string")

    @classmethod
    def build_curl(
        cls,
        parsed: ParsedCurl,
        params: Dict[str, Any]
    ) -> str:
        """
        使用参数重建 curl 命令

        Args:
            parsed: 解析后的 curl
            params: 参数值

        Returns:
            str: 完整的 curl 命令
        """
        parts = ["curl"]

        # 方法
        if parsed.method != "GET":
            parts.extend(["-X", parsed.method])

        # Headers
        for key, value in parsed.headers.items():
            parts.extend(["-H", f"{key}: {value}"])

        # URL with query params
        url = parsed.url
        query_parts = []
        for key, value in parsed.query_params.items():
            if key in params:
                query_parts.append(f"{key}={params[key]}")
            else:
                query_parts.append(f"{key}={value}")

        if query_parts:
            url += "?" + "&".join(query_parts)

        # Body
        if parsed.body and parsed.body_params:
            body_data = {}
            for key in parsed.body_params.keys():
                if key in params:
                    body_data[key] = params[key]
                else:
                    body_data[key] = parsed.body_params[key]

            if "json" in (parsed.content_type or "").lower():
                parts.extend(["-d", json.dumps(body_data, ensure_ascii=False)])
            else:
                body_str = "&".join([f"{k}={v}" for k, v in body_data.items()])
                parts.extend(["-d", body_str])

        parts.append(url)

        return " ".join(parts)
