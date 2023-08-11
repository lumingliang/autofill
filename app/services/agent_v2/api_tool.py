"""
API Tool 管理器

根据 OpenAPI 端点信息生成可执行的 LangChain Tools。
"""
import json
from typing import Dict, List, Any, Optional, Type, Callable

import httpx
from pydantic import BaseModel, Field, create_model
from langchain_core.tools import BaseTool, StructuredTool

from app.log import logger
from .openapi_parser import EndpointInfo, OpenAPIParser


class APIToolManager:
    """API Tool 管理器"""

    def __init__(
        self,
        parser: OpenAPIParser,
        api_key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ):
        """
        初始化 Tool 管理器

        Args:
            parser: OpenAPI 解析器实例
            api_key: API 密钥（可选）
            headers: 自定义请求头（可选）
            timeout: 请求超时时间（秒）
        """
        self.parser = parser
        self.api_key = api_key
        self.headers = headers or {}
        self.timeout = timeout
        self.base_url = parser.base_url

    def create_tools(self) -> List[BaseTool]:
        """为所有端点创建 Tools"""
        endpoints = self.parser.get_endpoints()
        tools = []

        for endpoint in endpoints:
            tool = self._create_tool(endpoint)
            if tool:
                tools.append(tool)

        logger.info(f"[APIToolManager] 创建了 {len(tools)} 个工具")
        return tools

    def _create_tool(self, endpoint: EndpointInfo) -> Optional[BaseTool]:
        """为单个端点创建 Tool"""
        try:
            # 构建参数 Schema
            args_schema = self._build_args_schema(endpoint)

            # 创建 API 调用函数
            api_caller = self._create_api_caller(endpoint)

            # 构建描述
            description = self._build_description(endpoint)

            return StructuredTool.from_function(
                coroutine=api_caller,
                name=endpoint.operation_id,
                description=description,
                args_schema=args_schema,
                return_direct=False,
            )

        except Exception as e:
            logger.error(f"[APIToolManager] 创建工具失败 {endpoint.operation_id}: {e}")
            return None

    def _build_args_schema(self, endpoint: EndpointInfo) -> Type[BaseModel]:
        """构建参数 Pydantic Schema"""
        fields = {}
        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        # 处理 Path/Query/Header 参数
        for param in endpoint.parameters:
            name = param.get("name", "")
            if not name:
                continue

            schema = param.get("schema", param)  # OpenAPI 3.0 vs 2.0
            ptype = schema.get("type", "string")
            desc = param.get("description", "")
            required = param.get("required", False)
            default = schema.get("default", None)

            py_type = type_mapping.get(ptype, str)

            if required:
                fields[name] = (py_type, Field(description=desc))
            else:
                fields[name] = (Optional[py_type], Field(default=default, description=desc))

        # 处理 Body 参数
        if endpoint.request_body:
            content = endpoint.request_body.get("content", {})
            json_schema = content.get("application/json", {}).get("schema", {})

            if json_schema:
                # 解析 Schema 属性
                properties = json_schema.get("properties", {})
                required_fields = json_schema.get("required", [])

                for name, prop in properties.items():
                    if name not in fields:  # 避免重复
                        ptype = prop.get("type", "string")
                        desc = prop.get("description", "")
                        required = name in required_fields
                        default = prop.get("default", None)

                        py_type = type_mapping.get(ptype, str)

                        if required:
                            fields[name] = (py_type, Field(description=desc))
                        else:
                            fields[name] = (Optional[py_type], Field(default=default, description=desc))

        # 创建动态 Pydantic 模型
        model_name = f"{endpoint.operation_id}Args".replace("-", "_").replace(".", "_")
        # 确保模型名是有效的 Python 标识符
        model_name = "".join(c if c.isalnum() or c == "_" else "_" for c in model_name)
        if model_name[0].isdigit():
            model_name = "_" + model_name

        return create_model(model_name, **fields)

    def _create_api_caller(self, endpoint: EndpointInfo) -> Callable:
        """创建 API 调用函数"""
        base_url = self.base_url
        path = endpoint.path
        method = endpoint.method.lower()
        api_key = self.api_key
        custom_headers = self.headers
        timeout = self.timeout

        async def api_caller(**kwargs) -> str:
            """执行 API 调用"""
            # 构建 URL
            url = f"{base_url}{path}"

            # 替换 path 参数
            path_params = {}
            query_params = {}
            body_params = {}

            for param in endpoint.parameters:
                name = param.get("name", "")
                param_in = param.get("in", "")

                if name in kwargs:
                    if param_in == "path":
                        path_params[name] = kwargs[name]
                    elif param_in == "query":
                        query_params[name] = kwargs[name]
                    elif param_in == "header":
                        custom_headers[name] = str(kwargs[name])

            # 替换 path 参数
            for name, value in path_params.items():
                url = url.replace(f"{{{name}}}", str(value))

            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                **custom_headers,
            }

            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                # 也支持 X-API-Key 格式
                headers["X-API-Key"] = api_key

            # 分离 body 参数
            body_param_names = set()
            if endpoint.request_body:
                content = endpoint.request_body.get("content", {})
                schema = content.get("application/json", {}).get("schema", {})
                body_param_names = set(schema.get("properties", {}).keys())

            for key, value in kwargs.items():
                if key not in path_params and key not in query_params:
                    if key in body_param_names:
                        body_params[key] = value
                    elif key not in [p.get("name") for p in endpoint.parameters]:
                        # 未在参数定义中的额外参数，放入 body
                        body_params[key] = value

            try:
                logger.info(f"[APIToolManager] 调用 API: {method.upper()} {url}")

                async with httpx.AsyncClient(timeout=timeout) as client:
                    if method == "get":
                        response = await client.get(url, headers=headers, params=query_params)
                    elif method in ["post", "put", "patch"]:
                        response = await client.request(
                            method=method,
                            url=url,
                            headers=headers,
                            params=query_params,
                            json=body_params if body_params else None
                        )
                    elif method == "delete":
                        response = await client.delete(url, headers=headers, params=query_params)
                    else:
                        return json.dumps({"error": f"Unsupported method: {method}"})

                response.raise_for_status()

                # 返回原始 JSON 字符串
                return response.text

            except httpx.TimeoutException:
                logger.error(f"[APIToolManager] API 调用超时: {url}")
                return json.dumps({"error": "Request timeout"})

            except httpx.HTTPStatusError as e:
                logger.error(f"[APIToolManager] API 调用失败: {e.response.status_code} - {e.response.text}")
                return json.dumps({
                    "error": f"HTTP {e.response.status_code}",
                    "detail": e.response.text
                })

            except Exception as e:
                logger.error(f"[APIToolManager] API 调用异常: {e}")
                return json.dumps({"error": str(e)})

        return api_caller

    def _build_description(self, endpoint: EndpointInfo) -> str:
        """构建工具描述"""
        lines = [
            f"API: {endpoint.summary or endpoint.operation_id}",
        ]

        if endpoint.description:
            lines.append(f"描述: {endpoint.description}")

        lines.append(f"方法: {endpoint.method} {endpoint.path}")

        # 添加参数说明
        if endpoint.parameters:
            lines.append("\n参数:")
            for p in endpoint.parameters:
                name = p.get("name", "")
                param_in = p.get("in", "")
                required = "必填" if p.get("required") else "可选"
                desc = p.get("description", "")
                lines.append(f"  - {name} ({param_in}, {required}): {desc}")

        # 添加 Body 参数说明
        if endpoint.request_body:
            content = endpoint.request_body.get("content", {})
            schema = content.get("application/json", {}).get("schema", {})
            properties = schema.get("properties", {})
            required_fields = schema.get("required", [])

            if properties:
                lines.append("\n请求体参数:")
                for name, prop in properties.items():
                    required = "必填" if name in required_fields else "可选"
                    desc = prop.get("description", "")
                    lines.append(f"  - {name} ({required}): {desc}")

        return "\n".join(lines)

    def get_tool_by_name(self, name: str) -> Optional[BaseTool]:
        """根据名称获取 Tool"""
        endpoints = self.parser.get_endpoints()

        for endpoint in endpoints:
            if endpoint.operation_id == name:
                return self._create_tool(endpoint)

        return None

    def get_tool_names(self) -> List[str]:
        """获取所有工具名称"""
        endpoints = self.parser.get_endpoints()
        return [ep.operation_id for ep in endpoints]
