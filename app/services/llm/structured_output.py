"""
结构化输出服务
实现6种结构化输出方法，支持多轮对话记忆（使用LangChain原生组件）
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union

import httpx
from langchain_core.output_parsers import PydanticOutputParser, JsonOutputParser
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, create_model

from app.log import logger
from app.models.llm_config import LLMConfig
from app.settings.config import settings


class SessionHistoryManager:
    """
    会话历史管理器 - 使用LangChain原生InMemoryChatMessageHistory
    支持滑动窗口记忆（通过max_rounds限制消息数量）
    """

    def __init__(self, max_rounds: int = 10):
        self.max_rounds = max_rounds
        self._histories: Dict[str, InMemoryChatMessageHistory] = {}

    def get_history(self, session_id: str) -> InMemoryChatMessageHistory:
        """获取或创建指定session的聊天历史"""
        if session_id not in self._histories:
            self._histories[session_id] = InMemoryChatMessageHistory()
        return self._histories[session_id]

    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """供RunnableWithMessageHistory使用的回调函数"""
        return self.get_history(session_id)

    def clear_session(self, session_id: str):
        """清除指定session的历史"""
        if session_id in self._histories:
            del self._histories[session_id]

    def trim_history(self, session_id: str, max_rounds: int = None):
        """
        修剪历史消息，保留最近N轮对话
        每轮对话包含一条HumanMessage和一条AIMessage
        """
        if session_id not in self._histories:
            return

        history = self._histories[session_id]
        max_rounds = max_rounds or self.max_rounds
        max_messages = max_rounds * 2  # 每轮2条消息

        messages = history.messages
        if len(messages) > max_messages:
            # 保留最近的消息
            history.messages = messages[-max_messages:]


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
    """结构化输出服务 - 支持多轮对话记忆（LangChain原生实现）"""

    # 默认方法优先级
    DEFAULT_METHOD_PRIORITY = [
        "with_structured_output",
        "bind_tools_stream",
        "custom_fc_non_stream",
        "custom_fc_stream",
        "pydantic_parser",
        "json_parser"
    ]

    # 类级别的历史管理器（所有实例共享）
    _history_manager = SessionHistoryManager(max_rounds=10)

    def __init__(self, config: LLMConfig):
        self.config = config
        self.litellm_params = config.litellm_params or {}
        
        # 使用配置名称作为模型名称（对应 LiteLLM 网关的 model_list 中的 model_name）
        # 而不是 litellm_params 中的 model（那是实际调用的模型标识）
        self.model_name = config.name
        
        self.api_key = self.litellm_params.get("api_key", "")
        self.api_base = self.litellm_params.get("api_base", None)
        self.timeout = self.litellm_params.get("timeout", 60)

        # 获取结构化输出配置
        self.structured_config = settings.STRUCTURED_OUTPUT_CONFIG
        self.failed_threshold = self.structured_config.get("failed_threshold", 2)
        self.enable_fallback = self.structured_config.get("enable_fallback", True)
        self.max_attempt_methods = self.structured_config.get("max_attempt_methods", 6)

    @classmethod
    def get_history_manager(cls) -> SessionHistoryManager:
        """获取历史管理器"""
        return cls._history_manager

    @classmethod
    def clear_session(cls, session_id: str):
        """清除指定session的历史"""
        cls._history_manager.clear_session(session_id)

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

    def _parse_text_function_call(self, content: str, tools: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        解析文本格式的 function call

        某些模型（如 DeepSeek）可能返回文本格式的 function call，例如：
        ▶︎call_api
        {
          "name": "比亚迪",
          "city": "重庆",
          ...
        }

        Args:
            content: LLM 返回的文本内容
            tools: 工具定义列表

        Returns:
            解析后的参数字典，如果不是 function call 格式则返回 None
        """
        if not content or not tools:
            return None

        import re

        # 获取第一个工具的名称
        first_tool = tools[0]
        if "function" in first_tool:
            tool_name = first_tool.get("function", {}).get("name", "")
        else:
            tool_name = first_tool.get("name", "")

        # 匹配 function call 标记和 JSON 内容
        # 支持格式: ▶︎call_api { ... } 或 ```json\n{...}\n```
        patterns = [
            # 匹配 ▶︎call_api {...} 格式
            rf'▶︎\s*{re.escape(tool_name)}\s*\n?({{.*?}})',
            rf'▶︎\s*call_\w+\s*\n?({{.*?}})',
            # 匹配 ```json\n{...}\n``` 格式
            r'```json\s*\n(.*?)\n```',
            # 匹配 ```\n{...}\n``` 格式
            r'```\s*\n(.*?)\n```',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                json_str = match.group(1).strip()
                try:
                    parsed = json.loads(json_str)
                    # 验证解析结果是否包含工具的参数
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    continue

        return None

    def _create_dynamic_model(self, tools: List[Dict[str, Any]]) -> Type[BaseModel]:
        """根据 tools 定义创建动态 Pydantic 模型

        合并所有工具的参数，所有字段都设为可选（Optional），
        以支持多工具场景下不同工具返回不同参数的情况。
        """
        if not tools:
            raise ValueError("tools 不能为空")

        from typing import Optional

        # 收集所有工具的参数
        all_properties = {}
        for tool in tools:
            # 支持两种格式：OpenAI 格式（有 function 字段）和简化格式（直接有 parameters）
            if "function" in tool:
                function_def = tool.get("function", {})
            else:
                function_def = tool
            parameters = function_def.get("parameters", {})
            properties = parameters.get("properties", {})
            all_properties.update(properties)

        # 构建字段定义 - 所有字段都设为 Optional，以支持多工具场景
        fields = {}
        for field_name, field_schema in all_properties.items():
            field_type = self._json_schema_to_python_type(field_schema)
            field_desc = field_schema.get("description", "")
            # 所有字段都设为 Optional，默认值为 None
            fields[field_name] = (Optional[field_type], Field(default=None, description=field_desc))

        # 创建动态模型
        model_name = "DynamicOutput"
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
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto",
        method: str = None
    ) -> StructuredOutputResult:
        """
        生成结构化输出，支持多轮对话记忆

        Args:
            query: 用户查询
            tools: 工具/函数定义列表
            system_prompt: 系统提示词
            session_id: 会话ID，用于多轮对话记忆
            memory_rounds: 记忆轮数限制，默认使用全局配置
            tool_choice: 工具选择模式，可选 "auto", "none", "required" 或指定工具名
            method: 指定使用的方法，可选 "with_structured_output", "bind_tools_stream",
                   "custom_fc_non_stream", "custom_fc_stream", "pydantic_parser", "json_parser"
                   如果为 None，则按优先级自动尝试

        Returns:
            StructuredOutputResult: 结构化输出结果
        """
        import time
        start_time = time.time()

        # 如果指定了方法，直接使用
        if method:
            try:
                result = await self._try_method(
                    method=method,
                    query=query,
                    tools=tools,
                    system_prompt=system_prompt,
                    session_id=session_id,
                    memory_rounds=memory_rounds,
                    tool_choice=tool_choice
                )
                if result.success:
                    result.latency_ms = int((time.time() - start_time) * 1000)
                return result
            except Exception as e:
                return StructuredOutputResult(
                    success=False,
                    error=f"{type(e).__name__}: {e}",
                    method=method
                )

        # 确定方法优先级
        methods_to_try = self._get_supported_methods()

        # 限制最大尝试方法数
        methods_to_try = methods_to_try[:self.max_attempt_methods]

        last_error = None
        result = None

        for method in methods_to_try:
            try:
                result = await self._try_method(
                    method=method,
                    query=query,
                    tools=tools,
                    system_prompt=system_prompt,
                    session_id=session_id,
                    memory_rounds=memory_rounds,
                    tool_choice=tool_choice
                )

                if result.success:
                    result.latency_ms = int((time.time() - start_time) * 1000)
                    break
                else:
                    last_error = result.error
                    # 记录失败
                    await self._record_method_failure(method, result.error)

            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                logger.error(f"Method {method} failed: {type(e).__name__}: {e}")
                await self._record_method_failure(method, f"{type(e).__name__}: {e}")

        if result and result.success:
            return result

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
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto"
    ) -> StructuredOutputResult:
        """尝试使用指定方法"""
        if method == "with_structured_output":
            return await self._method_with_structured_output(query, tools, system_prompt, session_id, memory_rounds, tool_choice)
        elif method == "bind_tools_non_stream":
            return await self._method_bind_tools_non_stream(query, tools, system_prompt, session_id, memory_rounds, tool_choice)
        elif method == "bind_tools_stream":
            return await self._method_bind_tools_stream(query, tools, system_prompt, session_id, memory_rounds, tool_choice)
        elif method == "custom_fc_non_stream":
            return await self._method_custom_fc_non_stream(query, tools, system_prompt, session_id, memory_rounds, tool_choice)
        elif method == "custom_fc_stream":
            return await self._method_custom_fc_stream(query, tools, system_prompt, session_id, memory_rounds, tool_choice)
        elif method == "pydantic_parser":
            return await self._method_pydantic_parser(query, tools, system_prompt, session_id, memory_rounds, tool_choice)
        elif method == "json_parser":
            return await self._method_json_parser(query, tools, system_prompt, session_id, memory_rounds, tool_choice)
        else:
            return StructuredOutputResult(
                success=False,
                error=f"未知方法: {method}",
                method=method
            )

    def _build_messages_with_history(
        self,
        query: str,
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None
    ) -> List[BaseMessage]:
        """
        构建消息列表，包含历史对话
        使用LangChain原生历史管理，通过trim_history实现滑动窗口
        """
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        # 添加历史消息（如果存在session_id）
        if session_id:
            # 先修剪历史，实现滑动窗口
            self._history_manager.trim_history(session_id, memory_rounds)
            history = self._history_manager.get_history(session_id)
            messages.extend(history.messages)

        # 添加当前查询
        messages.append(HumanMessage(content=query))

        return messages

    def _save_exchange_to_history(
        self,
        session_id: str,
        query: str,
        result: StructuredOutputResult
    ):
        """保存对话到历史记录"""
        if not session_id:
            return

        history = self._history_manager.get_history(session_id)
        history.add_user_message(query)
        assistant_response = json.dumps(result.data, ensure_ascii=False) if result.data else "{}"
        history.add_ai_message(assistant_response)
        logger.debug(f"Saved exchange to session: {session_id}")

    async def _method_with_structured_output(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto"
    ) -> StructuredOutputResult:
        """方法1: with_structured_output - LangChain 官方结构化输出

        使用 with_structured_output 直接获取结构化数据
        """
        try:
            llm = self._create_llm()
            DynamicModel = self._create_dynamic_model(tools)

            # 使用 with_structured_output
            structured_llm = llm.with_structured_output(DynamicModel)

            # 构建包含历史的messages
            messages = self._build_messages_with_history(query, system_prompt, session_id, memory_rounds)

            # 非流式调用
            result_data = await structured_llm.ainvoke(messages)

            result = StructuredOutputResult(
                success=True,
                data=result_data.model_dump(),
                method="with_structured_output"
            )
            self._save_exchange_to_history(session_id, query, result)
            return result

        except Exception as e:
            return StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method="with_structured_output"
            )

    async def _method_bind_tools_non_stream(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto"
    ) -> StructuredOutputResult:
        """方法1b: bind_tools + 非流式调用

        对于多工具场景，使用 bind_tools + 非流式调用。
        只取第一个 tool_call，确保每次只返回一个工具的参数。
        """
        try:
            llm = self._create_llm()

            # 转换 tools 为 LangChain 格式
            from langchain_core.utils.function_calling import convert_to_openai_tool
            lc_tools = [convert_to_openai_tool(t) for t in tools]

            # 使用 tool_choice="auto" 让 LLM 自动选择是否调用工具
            llm_with_tools = llm.bind_tools(lc_tools, tool_choice="auto")

            # 构建包含历史的messages
            messages = self._build_messages_with_history(query, system_prompt, session_id, memory_rounds)

            # 非流式调用
            response = await llm_with_tools.ainvoke(messages)

            # 检查是否有 tool calls - 只取第一个
            if hasattr(response, 'tool_calls') and response.tool_calls:
                # 只取第一个 tool_call，忽略其他的
                tool_call = response.tool_calls[0]
                args = tool_call.get("args", {})

                # 直接返回参数，不进行合并验证
                result = StructuredOutputResult(
                    success=True,
                    data=args,
                    method="bind_tools_non_stream"
                )
                self._save_exchange_to_history(session_id, query, result)
                return result
            else:
                # 如果没有 tool calls，检查 content 是否包含文本格式的 function call
                content = response.content if hasattr(response, 'content') else str(response)
                
                # 尝试解析文本格式的 function call (如 ▶︎call_api {...})
                parsed_args = self._parse_text_function_call(content, tools)
                if parsed_args is not None:
                    result = StructuredOutputResult(
                        success=True,
                        data=parsed_args,
                        method="bind_tools_non_stream"
                    )
                    self._save_exchange_to_history(session_id, query, result)
                    return result
                
                # 返回 LLM 的原始文本响应
                return StructuredOutputResult(
                    success=True,
                    data={"_raw_response": content},
                    method="bind_tools_non_stream"
                )

        except Exception as e:
            return StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method="bind_tools_non_stream"
            )

    async def _method_bind_tools_stream(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto"
    ) -> StructuredOutputResult:
        """方法2: bind_tools + 流式收集

        只取第一个 tool_call，确保每次只返回一个工具的参数。
        """
        try:
            llm = self._create_llm()

            # 转换 tools 为 LangChain 格式
            from langchain_core.utils.function_calling import convert_to_openai_tool
            lc_tools = [convert_to_openai_tool(t) for t in tools]

            # 使用 tool_choice="auto" 让 LLM 自动选择是否调用工具
            llm_with_tools = llm.bind_tools(lc_tools, tool_choice="auto")

            # 构建包含历史的messages
            messages = self._build_messages_with_history(query, system_prompt, session_id, memory_rounds)

            # 流式调用并收集 tool_calls 和文本内容
            tool_calls_data = []
            text_content = []
            async for chunk in llm_with_tools.astream(messages):
                if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                    tool_calls_data.extend(chunk.tool_calls)
                if hasattr(chunk, 'content') and chunk.content:
                    text_content.append(chunk.content)

            if tool_calls_data:
                # 只取第一个 tool_call 的参数，忽略其他的
                args = tool_calls_data[0].get("args", {})

                # 直接返回参数，不进行合并验证
                result = StructuredOutputResult(
                    success=True,
                    data=args,
                    method="bind_tools_stream"
                )
                self._save_exchange_to_history(session_id, query, result)
                return result
            else:
                # 如果没有收到 tool calls，检查文本内容是否包含 function call 标记
                content = "".join(text_content) if text_content else ""

                # 尝试解析文本格式的 function call (如 ▶︎call_api {...})
                parsed_args = self._parse_text_function_call(content, tools)
                if parsed_args is not None:
                    result = StructuredOutputResult(
                        success=True,
                        data=parsed_args,
                        method="bind_tools_stream"
                    )
                    self._save_exchange_to_history(session_id, query, result)
                    return result

                # 返回 LLM 的原始文本响应
                return StructuredOutputResult(
                    success=True,
                    data={"_raw_response": content},
                    method="bind_tools_stream"
                )

        except Exception as e:
            return StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method="bind_tools_stream"
            )

    async def _method_custom_fc_non_stream(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto"
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

            # 构建包含历史的messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # 添加历史消息
            if session_id:
                self._history_manager.trim_history(session_id, memory_rounds)
                history = self._history_manager.get_history(session_id)
                for msg in history.messages:
                    if isinstance(msg, HumanMessage):
                        messages.append({"role": "user", "content": msg.content})
                    elif isinstance(msg, AIMessage):
                        messages.append({"role": "assistant", "content": msg.content})

            messages.append({"role": "user", "content": query})

            payload = {
                "model": self.model_name,
                "messages": messages,
                "tools": tools,
                "tool_choice": tool_choice
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                result_data = response.json()

            # 解析 tool_calls
            message = result_data.get("choices", [{}])[0].get("message", {})
            tool_calls = message.get("tool_calls", [])

            if tool_calls:
                args = json.loads(tool_calls[0].get("function", {}).get("arguments", "{}"))
                validated = DynamicModel(**args)

                result = StructuredOutputResult(
                    success=True,
                    data=validated.model_dump(),
                    method="custom_fc_non_stream",
                    prompt_tokens=result_data.get("usage", {}).get("prompt_tokens", 0),
                    completion_tokens=result_data.get("usage", {}).get("completion_tokens", 0)
                )
                self._save_exchange_to_history(session_id, query, result)
                return result
            else:
                # 如果没有 tool_calls，检查 content 是否包含文本格式的 function call
                content = message.get("content", "")
                if content:
                    parsed_args = self._parse_text_function_call(content, tools)
                    if parsed_args is not None:
                        validated = DynamicModel(**parsed_args)
                        result = StructuredOutputResult(
                            success=True,
                            data=validated.model_dump(),
                            method="custom_fc_non_stream",
                            prompt_tokens=result_data.get("usage", {}).get("prompt_tokens", 0),
                            completion_tokens=result_data.get("usage", {}).get("completion_tokens", 0)
                        )
                        self._save_exchange_to_history(session_id, query, result)
                        return result
                
                return StructuredOutputResult(
                    success=False,
                    error="No tool calls in response",
                    method="custom_fc_non_stream"
                )

        except Exception as e:
            return StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method="custom_fc_non_stream"
            )

    async def _method_custom_fc_stream(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto"
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

            # 构建包含历史的messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # 添加历史消息
            if session_id:
                self._history_manager.trim_history(session_id, memory_rounds)
                history = self._history_manager.get_history(session_id)
                for msg in history.messages:
                    if isinstance(msg, HumanMessage):
                        messages.append({"role": "user", "content": msg.content})
                    elif isinstance(msg, AIMessage):
                        messages.append({"role": "assistant", "content": msg.content})

            messages.append({"role": "user", "content": query})

            payload = {
                "model": self.model_name,
                "messages": messages,
                "tools": tools,
                "tool_choice": tool_choice,
                "stream": True
            }

            # 收集流式响应中的 tool_calls
            tool_calls_buffer = {}

            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/v1/chat/completions",
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

                result = StructuredOutputResult(
                    success=True,
                    data=validated.model_dump(),
                    method="custom_fc_stream"
                )
                self._save_exchange_to_history(session_id, query, result)
                return result
            else:
                return StructuredOutputResult(
                    success=False,
                    error="No tool calls in stream response",
                    method="custom_fc_stream"
                )

        except Exception as e:
            return StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method="custom_fc_stream"
            )

    async def _method_pydantic_parser(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto"
    ) -> StructuredOutputResult:
        """方法5: PydanticOutputParser"""
        try:
            llm = self._create_llm()
            DynamicModel = self._create_dynamic_model(tools)
            parser = PydanticOutputParser(pydantic_object=DynamicModel)

            # 构建提示模板
            format_instructions = parser.get_format_instructions()

            # 构建工具描述
            tools_description = self._build_tools_description(tools)

            # 使用LangChain原生历史管理
            history_messages = []
            if session_id:
                self._history_manager.trim_history(session_id, memory_rounds)
                history = self._history_manager.get_history(session_id)
                for msg in history.messages:
                    if isinstance(msg, HumanMessage):
                        history_messages.append(f"User: {msg.content}")
                    elif isinstance(msg, AIMessage):
                        history_messages.append(f"Assistant: {msg.content}")

            history_text = "\n".join(history_messages) + "\n\n" if history_messages else ""

            prompt_text = f"""{system_prompt or 'You are a helpful assistant.'}

Available tools:
{tools_description}

You must respond with a JSON object indicating which tool to use and its parameters.

Please provide your response in the following JSON format:
{format_instructions}

{history_text}User query: {query}
"""

            messages = [HumanMessage(content=prompt_text)]
            response = await llm.ainvoke(messages)
            content = response.content

            # 解析结果
            parsed = parser.parse(content)

            result = StructuredOutputResult(
                success=True,
                data=parsed.model_dump(),
                method="pydantic_parser"
            )
            self._save_exchange_to_history(session_id, query, result)
            return result

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

                result = StructuredOutputResult(
                    success=True,
                    data=validated.model_dump(),
                    method="pydantic_parser"
                )
                self._save_exchange_to_history(session_id, query, result)
                return result
            except Exception as inner_e:
                return StructuredOutputResult(
                    success=False,
                    error=f"{type(inner_e).__name__}: {inner_e}",
                    method="pydantic_parser"
                )

        except Exception as e:
            return StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method="pydantic_parser"
            )

    async def _method_json_parser(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto"
    ) -> StructuredOutputResult:
        """方法6: JsonOutputParser"""
        try:
            llm = self._create_llm()
            DynamicModel = self._create_dynamic_model(tools)
            parser = JsonOutputParser(pydantic_object=DynamicModel)

            # 构建提示模板
            format_instructions = parser.get_format_instructions()

            # 构建工具描述
            tools_description = self._build_tools_description(tools)

            # 使用LangChain原生历史管理
            history_messages = []
            if session_id:
                self._history_manager.trim_history(session_id, memory_rounds)
                history = self._history_manager.get_history(session_id)
                for msg in history.messages:
                    if isinstance(msg, HumanMessage):
                        history_messages.append(f"User: {msg.content}")
                    elif isinstance(msg, AIMessage):
                        history_messages.append(f"Assistant: {msg.content}")

            history_text = "\n".join(history_messages) + "\n\n" if history_messages else ""

            prompt_text = f"""{system_prompt or 'You are a helpful assistant.'}

Available tools:
{tools_description}

You must respond with a JSON object indicating which tool to use and its parameters.

Please provide your response in the following JSON format:
{format_instructions}

{history_text}User query: {query}
"""

            messages = [HumanMessage(content=prompt_text)]
            response = await llm.ainvoke(messages)
            content = response.content

            # 解析结果
            parsed = parser.parse(content)

            result = StructuredOutputResult(
                success=True,
                data=parsed,
                method="json_parser"
            )
            self._save_exchange_to_history(session_id, query, result)
            return result

        except Exception as e:
            # 尝试直接解析 JSON
            try:
                content = str(e)
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                data = json.loads(content.strip())

                result = StructuredOutputResult(
                    success=True,
                    data=data,
                    method="json_parser"
                )
                self._save_exchange_to_history(session_id, query, result)
                return result
            except Exception as inner_e:
                return StructuredOutputResult(
                    success=False,
                    error=f"{type(inner_e).__name__}: {inner_e}",
                    method="json_parser"
                )

    def _build_tools_description(self, tools: List[Dict[str, Any]]) -> str:
        """构建工具描述文本"""
        descriptions = []
        for tool in tools:
            if "function" in tool:
                func = tool["function"]
                name = func.get("name", "unknown")
                desc = func.get("description", "")
                params = func.get("parameters", {})
                param_desc = ""
                if "properties" in params:
                    for prop_name, prop_info in params["properties"].items():
                        prop_desc = prop_info.get("description", "")
                        param_desc += f"\n      - {prop_name}: {prop_desc}"
                descriptions.append(f"  - {name}: {desc}{param_desc}")
        return "\n".join(descriptions)

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
