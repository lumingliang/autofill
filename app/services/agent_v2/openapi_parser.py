"""
OpenAPI 规范解析器

解析 OpenAPI/Swagger 规范，提取 API 端点信息。
"""
import json
from typing import Dict, List, Any, Optional

import httpx
import yaml

from app.log import logger


class EndpointInfo:
    """API 端点信息"""

    def __init__(
        self,
        path: str,
        method: str,
        operation_id: str = "",
        summary: str = "",
        description: str = "",
        parameters: List[Dict] = None,
        request_body: Dict = None,
        responses: Dict = None,
        tags: List[str] = None
    ):
        self.path = path
        self.method = method.upper()
        self.operation_id = operation_id or f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '')}"
        self.summary = summary
        self.description = description
        self.parameters = parameters or []
        self.request_body = request_body or {}
        self.responses = responses or {}
        self.tags = tags or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "path": self.path,
            "method": self.method,
            "operation_id": self.operation_id,
            "summary": self.summary,
            "description": self.description,
            "parameters": self.parameters,
            "request_body": self.request_body,
            "responses": self.responses,
            "tags": self.tags,
        }


class OpenAPIParser:
    """OpenAPI 规范解析器"""

    def __init__(self, spec_source: str):
        """
        初始化解析器

        Args:
            spec_source: OpenAPI 规范来源，可以是 URL 或本地文件路径
        """
        self.spec = self._load_spec(spec_source)
        self.base_url = self._get_base_url()
        self.title = self.spec.get("info", {}).get("title", "")
        self.version = self.spec.get("info", {}).get("version", "")
        self.description = self.spec.get("info", {}).get("description", "")

    def _load_spec(self, source: str) -> Dict:
        """加载 OpenAPI 规范"""
        logger.info(f"[OpenAPIParser] 加载规范: {source[:100]}...")

        try:
            # 检查是否是直接的 JSON 字符串
            source_stripped = source.strip()
            if source_stripped.startswith("{") and source_stripped.endswith("}"):
                try:
                    return json.loads(source)
                except json.JSONDecodeError:
                    pass

            # 检查是否是 YAML 字符串
            if source_stripped.startswith("openapi:") or source_stripped.startswith("swagger:"):
                try:
                    return yaml.safe_load(source)
                except yaml.YAMLError:
                    pass

            if source.startswith(("http://", "https://")):
                # 从 URL 加载
                response = httpx.get(source, timeout=30)
                response.raise_for_status()
                content = response.text
            else:
                # 从本地文件加载
                with open(source, "r", encoding="utf-8") as f:
                    content = f.read()

            # 解析 JSON 或 YAML
            if content.strip().startswith("{"):
                return json.loads(content)
            return yaml.safe_load(content)

        except Exception as e:
            logger.error(f"[OpenAPIParser] 加载规范失败: {e}")
            raise ValueError(f"Failed to load OpenAPI spec: {e}")

    def _get_base_url(self) -> str:
        """获取基础 URL"""
        servers = self.spec.get("servers", [])
        if servers:
            return servers[0].get("url", "")

        # 尝试从 host + basePath 获取 (Swagger 2.0)
        host = self.spec.get("host", "")
        base_path = self.spec.get("basePath", "")
        schemes = self.spec.get("schemes", ["http"])

        if host:
            scheme = schemes[0] if schemes else "http"
            return f"{scheme}://{host}{base_path}"

        return ""

    def get_endpoints(self) -> List[EndpointInfo]:
        """提取所有 API 端点"""
        endpoints = []
        paths = self.spec.get("paths", {})

        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() in ["get", "post", "put", "delete", "patch"]:
                    endpoint = self._parse_endpoint(path, method, details)
                    endpoints.append(endpoint)

        logger.info(f"[OpenAPIParser] 解析到 {len(endpoints)} 个端点")
        return endpoints

    def _parse_endpoint(self, path: str, method: str, details: Dict) -> EndpointInfo:
        """解析单个端点"""
        # 处理 $ref 引用
        if "$ref" in details:
            details = self._resolve_ref(details["$ref"])

        return EndpointInfo(
            path=path,
            method=method.lower(),
            operation_id=details.get("operationId", ""),
            summary=details.get("summary", ""),
            description=details.get("description", ""),
            parameters=details.get("parameters", []),
            request_body=details.get("requestBody", {}),
            responses=details.get("responses", {}),
            tags=details.get("tags", []),
        )

    def _resolve_ref(self, ref: str) -> Dict:
        """解析 $ref 引用"""
        if not ref.startswith("#/"):
            return {}

        parts = ref[2:].split("/")
        current = self.spec

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return {}

        return current if isinstance(current, dict) else {}

    def get_schemas(self) -> Dict[str, Dict]:
        """获取所有 Schema 定义"""
        # OpenAPI 3.0
        schemas = self.spec.get("components", {}).get("schemas", {})

        # Swagger 2.0
        if not schemas:
            schemas = self.spec.get("definitions", {})

        return schemas

    def get_security_schemes(self) -> Dict[str, Dict]:
        """获取安全方案定义"""
        # OpenAPI 3.0
        schemes = self.spec.get("components", {}).get("securitySchemes", {})

        # Swagger 2.0
        if not schemes:
            schemes = self.spec.get("securityDefinitions", {})

        return schemes

    def get_global_security(self) -> List[Dict]:
        """获取全局安全要求"""
        return self.spec.get("security", [])
