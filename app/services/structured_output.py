"""
结构化输出服务
实现6种结构化输出方法
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union

import httpx
from langchain_core.output_parsers import PydanticOutputParser, JsonOutputParser
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, create_model

from app.models.llm_config import LLMConfig
from app.settings.config import settings

logger = logging.getLogger(__name__)


class StructuredOutputResult:
    """结构化输出结果"""
    def __init__(
        self,
        success: bool,
        data: Dict[str, Any] = None,
        method: str = "",
        error: str = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0
    ):
        self.success = success
        self.data = data or {}
        self.method = method
        self.error = error
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.latency_ms = 0


class StructuredOutputService:
    """结构化输出服务"""

    # 默认方法优先级
    DEFAULT_METHOD_PRIORITY = [
        "with_structured_output",
        "bind_tools_stream",
        "custom_fc_non_stream",
        "custom_fc_stream",
        "pydantic_parser",
        "json_parser"
    ]

    def __init__(self, config: LLMConfig):
        self.config = config
        self.litellm_params = config.litellm_params or {}
        self.model_name = self.litellm_params.get("model", "gpt-3.5-turbo")
        self.api_key = self.litellm_params.get("api_key", "")
        self.api_base = self.litellm_params.get("api_base", None)
        self.timeout = self.litellm_params.get("timeout", 60)

        # 获取结构化输出配置
        self.structured_config = settings.STRUCTURED_OUTPUT_CONFIG
        self.failed_threshold = self.structured_config.get("failed_threshold", 2)
        self.enable_fallback = self.structured_config.get("enable_fallback", True)
        self.max_attempt_methods = self.structured_config.get("max_attempt_methods", 6)

    def _create_llm(self, temperature: float = 0.0) -> ChatOpenAI:
        """创建 LangChain LLM 实例"""
        # 使用 LiteLLM 网关
        litellm_config = settings.LITELLM_CONFIG
        base_url = litellm_config.get("base_url", "http://localhost:4000")
        master_key = litellm_config.get("master_key", "")

        return ChatOpenAI(
            model=self.model_name,
            api_key=master_key,
            base_url=f"{base_url}/v1",
            temperature=temperature,
            timeout=self.timeout
        )

    def _create_dynamic_model(self, tools: List[Dict[str, Any]]) -> Type[BaseModel]:
        """根据 tools 定义创建动态 Pydantic 模型"""
        if not tools:
            raise ValueError("tools 不能为空")

        tool = tools[0]
        # 支持两种格式：OpenAI 格式（有 function 字段）和简化格式（直接有 parameters）
        if "function" in tool:
            function_def = tool.get("function", {})
        else:
            function_def = tool
        parameters = function_def.get("parameters", {})
        properties = parameters.get("properties", {})
        required = parameters.get("required", [])

        # 构建字段定义
        fields = {}
        for field_name, field_schema in properties.items():
            field_type = self._json_schema_to_python_type(field_schema)
            field_desc = field_schema.get("description", "")
            field_default = ... if field_name in required else None
            fields[field_name] = (field_type, Field(default=field_default, description=field_desc))

        # 创建动态模型
        model_name = function_def.get("name", "DynamicOutput").replace("_", " ").title().replace(" ", "")
        return create_model(model_name, **fields)

    def _json_schema_to_python_type(self, schema: Dict[str, Any]) -> Type:
        """将 JSON Schema 类型转换为 Python 类型"""
        json_type = schema.get("type", "string")

        if json_type == "string":
            enum = schema.get("enum")
            if enum:
                from typing import Literal
                return Literal[tuple(enum)]
            return str
        elif json_type == "integer":
            return int
        elif json_type == "number":
            return float
        elif json_type == "boolean":
            return bool
        elif json_type == "array":
            items = schema.get("items", {})
            item_type = self._json_schema_to_python_type(items)
            from typing import List
            return List[item_type]
        elif json_type == "object":
            return Dict[str, Any]
        else:
            return str

    def _get_supported_methods(self) -> List[str]:
        """获取支持的方法列表（根据 capabilities）"""
        capabilities = self.config.capabilities or {}
        structured_methods = capabilities.get("structured_output_methods", {})

        supported = []
        for method in self.DEFAULT_METHOD_PRIORITY:
            method_config = structured_methods.get(method, {})
            if method_config.get("supported", True):
                supported.append(method)

        return supported

    async def generate(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        context: str = None,
        preferred_methods: List[str] = None
    ) -> StructuredOutputResult:
        """
        生成结构化输出

        Args:
            query: 用户查询
            tools: 工具/函数定义列表
            system_prompt: 系统提示词
            context: 额外上下文
            preferred_methods: 优先使用方法列表

        Returns:
            StructuredOutputResult: 结构化输出结果
        """
        import time
        start_time = time.time()

        # 确定方法优先级
        if preferred_methods:
            methods_to_try = preferred_methods
        else:
            methods_to_try = self._get_supported_methods()

        # 限制最大尝试方法数
        methods_to_try = methods_to_try[:self.max_attempt_methods]

        last_error = None

        for method in methods_to_try:
            try:
                result = await self._try_method(
                    method=method,
                    query=query,
                    tools=tools,
                    system_prompt=system_prompt,
                    context=context
                )

                if result.success:
                    result.latency_ms = int((time.time() - start_time) * 1000)
                    return result
                else:
                    last_error = result.error
                    # 记录失败
                    await self._record_method_failure(method, result.error)

            except Exception as e:
                last_error = str(e)
                logger.error(f"Method {method} failed: {e}")
                await self._record_method_failure(method, str(e))

        # 所有方法都失败
        return StructuredOutputResult(
            success=False,
            error=f"所有方法都失败，最后错误: {last_error}",
            method="none"
        )

    async def _try_method(
        self,
        method: str,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        context: str = None
    ) -> StructuredOutputResult:
        """尝试使用指定方法"""
        if method == "with_structured_output":
            return await self._method_with_structured_output(query, tools, system_prompt, context)
        elif method == "bind_tools_stream":
            return await self._method_bind_tools_stream(query, tools, system_prompt, context)
        elif method == "custom_fc_non_stream":
            return await self._method_custom_fc_non_stream(query, tools, system_prompt, context)
        elif method == "custom_fc_stream":
            return await self._method_custom_fc_stream(query, tools, system_prompt, context)
        elif method == "pydantic_parser":
            return await self._method_pydantic_parser(query, tools, system_prompt, context)
        elif method == "json_parser":
            return await self._method_json_parser(query, tools, system_prompt, context)
        else:
            return StructuredOutputResult(
                success=False,
                error=f"未知方法: {method}",
                method=method
            )

    async def _method_with_structured_output(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        context: str = None
    ) -> StructuredOutputResult:
        """方法1: with_structured_output - LangChain 官方 Function Calling"""
        try:
            llm = self._create_llm()
            DynamicModel = self._create_dynamic_model(tools)

            structured_llm = llm.with_structured_output(DynamicModel)

            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            if context:
                messages.append(SystemMessage(content=f"Context: {context}"))
            messages.append(HumanMessage(content=query))

            result = await structured_llm.ainvoke(messages)

            return StructuredOutputResult(
                success=True,
                data=result.model_dump(),
                method="with_structured_output"
            )

        except Exception as e:
            return StructuredOutputResult(
                success=False,
                error=str(e),
                method="with_structured_output"
            )

    async def _method_bind_tools_stream(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        context: str = None
    ) -> StructuredOutputResult:
        """方法2: bind_tools + 流式收集"""
        try:
            llm = self._create_llm()
            DynamicModel = self._create_dynamic_model(tools)

            # 转换 tools 为 LangChain 格式
            from langchain_core.utils.function_calling import convert_to_openai_tool
            lc_tools = [convert_to_openai_tool(t) for t in tools]

            llm_with_tools = llm.bind_tools(lc_tools)

            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            if context:
                messages.append(SystemMessage(content=f"Context: {context}"))
            messages.append(HumanMessage(content=query))

            # 流式调用并收集 tool_calls
            tool_calls_data = []
            async for chunk in llm_with_tools.astream(messages):
                if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                    tool_calls_data.extend(chunk.tool_calls)

            if tool_calls_data:
                # 解析第一个 tool_call 的参数
                args = tool_calls_data[0].get("args", {})
                # 验证
                validated = DynamicModel(**args)
                return StructuredOutputResult(
                    success=True,
                    data=validated.model_dump(),
                    method="bind_tools_stream"
                )
            else:
                return StructuredOutputResult(
                    success=False,
                    error="No tool calls received",
                    method="bind_tools_stream"
                )

        except Exception as e:
            return StructuredOutputResult(
                success=False,
                error=str(e),
                method="bind_tools_stream"
            )

    async def _method_custom_fc_non_stream(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        context: str = None
    ) -> StructuredOutputResult:
        """方法3: 自定义 FC 非流式"""
        try:
            DynamicModel = self._create_dynamic_model(tools)

            # 使用 LiteLLM 网关
            litellm_config = settings.LITELLM_CONFIG
            base_url = litellm_config.get("base_url", "http://localhost:4000")
            master_key = litellm_config.get("master_key", "")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {master_key}"
            }

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if context:
                messages.append({"role": "system", "content": f"Context: {context}"})
            messages.append({"role": "user", "content": query})

            payload = {
                "model": self.model_name,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()

            # 解析 tool_calls
            message = result.get("choices", [{}])[0].get("message", {})
            tool_calls = message.get("tool_calls", [])

            if tool_calls:
                args = json.loads(tool_calls[0].get("function", {}).get("arguments", "{}"))
                validated = DynamicModel(**args)
                return StructuredOutputResult(
                    success=True,
                    data=validated.model_dump(),
                    method="custom_fc_non_stream",
                    prompt_tokens=result.get("usage", {}).get("prompt_tokens", 0),
                    completion_tokens=result.get("usage", {}).get("completion_tokens", 0)
                )
            else:
                return StructuredOutputResult(
                    success=False,
                    error="No tool calls in response",
                    method="custom_fc_non_stream"
                )

        except Exception as e:
            return StructuredOutputResult(
                success=False,
                error=str(e),
                method="custom_fc_non_stream"
            )

    async def _method_custom_fc_stream(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        context: str = None
    ) -> StructuredOutputResult:
        """方法4: 自定义 FC 流式"""
        try:
            DynamicModel = self._create_dynamic_model(tools)

            # 使用 LiteLLM 网关
            litellm_config = settings.LITELLM_CONFIG
            base_url = litellm_config.get("base_url", "http://localhost:4000")
            master_key = litellm_config.get("master_key", "")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {master_key}"
            }

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if context:
                messages.append({"role": "system", "content": f"Context: {context}"})
            messages.append({"role": "user", "content": query})

            payload = {
                "model": self.model_name,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "stream": True
            }

            # 收集流式响应中的 tool_calls
            tool_calls_buffer = {}

            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                tc = delta.get("tool_calls", [])
                                for t in tc:
                                    idx = t.get("index", 0)
                                    if idx not in tool_calls_buffer:
                                        tool_calls_buffer[idx] = {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
                                    if t.get("id"):
                                        tool_calls_buffer[idx]["id"] = t["id"]
                                    if t.get("function", {}).get("name"):
                                        tool_calls_buffer[idx]["function"]["name"] = t["function"]["name"]
                                    if t.get("function", {}).get("arguments"):
                                        tool_calls_buffer[idx]["function"]["arguments"] += t["function"]["arguments"]
                            except:
                                pass

            if tool_calls_buffer:
                first_tc = tool_calls_buffer[0]
                args = json.loads(first_tc.get("function", {}).get("arguments", "{}"))
                validated = DynamicModel(**args)
                return StructuredOutputResult(
                    success=True,
                    data=validated.model_dump(),
                    method="custom_fc_stream"
                )
            else:
                return StructuredOutputResult(
                    success=False,
                    error="No tool calls in stream response",
                    method="custom_fc_stream"
                )

        except Exception as e:
            return StructuredOutputResult(
                success=False,
                error=str(e),
                method="custom_fc_stream"
            )

    async def _method_pydantic_parser(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        context: str = None
    ) -> StructuredOutputResult:
        """方法5: PydanticOutputParser"""
        try:
            llm = self._create_llm()
            DynamicModel = self._create_dynamic_model(tools)
            parser = PydanticOutputParser(pydantic_object=DynamicModel)

            # 构建提示模板
            format_instructions = parser.get_format_instructions()

            prompt_text = f"""{system_prompt or 'You are a helpful assistant.'}

{context if context else ''}

Please provide your response in the following JSON format:
{format_instructions}

User query: {query}
"""

            messages = [HumanMessage(content=prompt_text)]
            response = await llm.ainvoke(messages)
            content = response.content

            # 解析结果
            parsed = parser.parse(content)

            return StructuredOutputResult(
                success=True,
                data=parsed.model_dump(),
                method="pydantic_parser"
            )

        except OutputParserException as e:
            # 尝试修复 JSON
            try:
                content = str(e.llm_output) if hasattr(e, 'llm_output') else str(e)
                # 提取 JSON 部分
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                data = json.loads(content.strip())
                validated = DynamicModel(**data)
                return StructuredOutputResult(
                    success=True,
                    data=validated.model_dump(),
                    method="pydantic_parser"
                )
            except:
                return StructuredOutputResult(
                    success=False,
                    error=str(e),
                    method="pydantic_parser"
                )

        except Exception as e:
            return StructuredOutputResult(
                success=False,
                error=str(e),
                method="pydantic_parser"
            )

    async def _method_json_parser(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        context: str = None
    ) -> StructuredOutputResult:
        """方法6: JsonOutputParser"""
        try:
            llm = self._create_llm()
            DynamicModel = self._create_dynamic_model(tools)
            parser = JsonOutputParser(pydantic_object=DynamicModel)

            # 构建提示模板
            format_instructions = parser.get_format_instructions()

            prompt_text = f"""{system_prompt or 'You are a helpful assistant.'}

{context if context else ''}

Please provide your response in the following JSON format:
{format_instructions}

User query: {query}
"""

            messages = [HumanMessage(content=prompt_text)]
            response = await llm.ainvoke(messages)
            content = response.content

            # 解析结果
            parsed = parser.parse(content)

            return StructuredOutputResult(
                success=True,
                data=parsed,
                method="json_parser"
            )

        except Exception as e:
            # 尝试直接解析 JSON
            try:
                content = str(e)
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                data = json.loads(content.strip())
                return StructuredOutputResult(
                    success=True,
                    data=data,
                    method="json_parser"
                )
            except:
                return StructuredOutputResult(
                    success=False,
                    error=str(e),
                    method="json_parser"
                )

    async def _record_method_failure(self, method: str, error: str):
        """记录方法失败"""
        from app.controllers.llm_config import llm_config_controller

        capabilities = self.config.capabilities or LLMConfig.get_default_capabilities()
        structured_methods = capabilities.get("structured_output_methods", {})

        if method in structured_methods:
            method_config = structured_methods[method]
            method_config["failed_count"] = method_config.get("failed_count", 0) + 1
            method_config["last_error"] = error
            method_config["last_attempt"] = datetime.now().isoformat()

            # 检查是否超过阈值
            if method_config["failed_count"] >= self.failed_threshold:
                method_config["supported"] = False
                logger.warning(f"Method {method} marked as unsupported after {method_config['failed_count']} failures")

            # 保存更新
            await llm_config_controller.update_method_status(
                id=self.config.id,
                method=method,
                supported=method_config["supported"],
                failed_count=method_config["failed_count"],
                last_error=error
            )
