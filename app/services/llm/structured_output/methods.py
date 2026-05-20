"""
结构化输出方法实现
"""
import json
import time
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI

from app.log import logger
from app.services.llm.structured_output.history_manager import SessionHistoryManager
from app.services.llm.structured_output.result import StructuredOutputResult
from app.services.llm.structured_output.schema_builder import FCSchemaBuilder
from app.services.llm.structured_output.utils import parse_text_function_call


class StructuredOutputMethods:
    """结构化输出方法集合"""

    def __init__(self, model_name: str, api_key: str, base_url: str, timeout: int = 300):
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

    def _create_llm(self, temperature: float = 0.0) -> ChatOpenAI:
        """创建 LangChain LLM 实例"""
        return ChatOpenAI(
            model=self.model_name,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=temperature,
            timeout=self.timeout
        )

    def _build_messages_with_history(
        self,
        query: str,
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None,
        history_manager: SessionHistoryManager = None
    ) -> List[BaseMessage]:
        """构建消息列表，包含历史对话"""
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        if session_id and history_manager:
            history_manager.trim_history(session_id, memory_rounds)
            history = history_manager.get_history(session_id)
            messages.extend(history.messages)

        messages.append(HumanMessage(content=query))
        return messages

    def _save_exchange_to_history(
        self,
        session_id: str,
        query: str,
        result: StructuredOutputResult,
        history_manager: SessionHistoryManager
    ):
        """保存对话到历史记录"""
        if not session_id or not history_manager:
            return

        history = history_manager.get_history(session_id)
        history.add_user_message(query)
        assistant_response = json.dumps(result.data, ensure_ascii=False) if result.data else "{}"
        history.add_ai_message(assistant_response)
        logger.debug(f"Saved exchange to session: {session_id}")

    async def method_with_structured_output(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto",
        history_manager: SessionHistoryManager = None
    ) -> StructuredOutputResult:
        """方法1: with_structured_output - LangChain 官方结构化输出

        注意: 此方法使用 tool_call，禁止使用传入的 system_prompt，仅使用简单的 tool_call 系统提示词
        """
        start_time = time.time()
        method_name = "with_structured_output"

        tool_call_system_prompt = "You are a helpful assistant that can use tools to complete tasks."

        try:
            llm = self._create_llm()

            # 使用第一个 tool 的 schema 创建 Pydantic 模型
            fc_schema = tools[0] if tools else {}
            DynamicModel = FCSchemaBuilder.build_pydantic_model_from_fc(fc_schema)
            structured_llm = llm.with_structured_output(DynamicModel)
            messages = self._build_messages_with_history(
                query, tool_call_system_prompt, session_id, memory_rounds, history_manager
            )

            result_data = await structured_llm.ainvoke(messages)

            latency_ms = (time.time() - start_time) * 1000

            result = StructuredOutputResult(
                success=True,
                data=result_data.model_dump(),
                method=method_name,
                latency_ms=latency_ms
            )

            self._save_exchange_to_history(session_id, query, result, history_manager)
            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            result = StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method=method_name,
                latency_ms=latency_ms
            )

            return result

    async def method_bind_tools_non_stream(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto",
        history_manager: SessionHistoryManager = None
    ) -> StructuredOutputResult:
        """方法2: bind_tools + 非流式调用

        注意: 此方法使用 tool_call，禁止使用传入的 system_prompt，仅使用简单的 tool_call 系统提示词
        """
        start_time = time.time()
        method_name = "bind_tools_non_stream"

        tool_call_system_prompt = "You are a helpful assistant that can use tools to complete tasks."

        try:
            llm = self._create_llm()
            lc_tools = [convert_to_openai_tool(t) for t in tools]
            llm_with_tools = llm.bind_tools(lc_tools, tool_choice="auto")
            messages = self._build_messages_with_history(
                query, tool_call_system_prompt, session_id, memory_rounds, history_manager
            )

            response = await llm_with_tools.ainvoke(messages)

            latency_ms = (time.time() - start_time) * 1000

            if hasattr(response, 'tool_calls') and response.tool_calls:
                tool_call = response.tool_calls[0]
                args = tool_call.get("args", {})
                result = StructuredOutputResult(
                    success=True,
                    data=args,
                    method=method_name,
                    latency_ms=latency_ms
                )

                self._save_exchange_to_history(session_id, query, result, history_manager)
                return result
            else:
                content = response.content if hasattr(response, 'content') else str(response)
                parsed_args = parse_text_function_call(content, tools)
                if parsed_args is not None:
                    result = StructuredOutputResult(
                        success=True,
                        data=parsed_args,
                        method=method_name,
                        latency_ms=latency_ms
                    )

                    self._save_exchange_to_history(session_id, query, result, history_manager)
                    return result

                result = StructuredOutputResult(
                    success=False,
                    error="No tool calls in response",
                    method=method_name,
                    latency_ms=latency_ms
                )

                return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            result = StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method=method_name,
                latency_ms=latency_ms
            )

            return result

    async def method_plain(
        self,
        query: str,
        system_prompt: str = None,
        field_specs: List[Dict[str, Any]] = None,
        include_reason: bool = False,
        session_id: str = None,
        memory_rounds: int = None,
        history_manager: SessionHistoryManager = None
    ) -> StructuredOutputResult:
        """方法8: plain - 纯文本模式，直接返回LLM的原始响应

        此方法不使用任何结构化输出机制，直接返回原始文本响应。
        适用于简单的聊天场景，不需要提取结构化数据。
        """
        start_time = time.time()
        method_name = "plain"

        try:
            llm = self._create_llm()

            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))

            if session_id and history_manager:
                history_manager.trim_history(session_id, memory_rounds)
                history = history_manager.get_history(session_id)
                messages.extend(history.messages)

            messages.append(HumanMessage(content=query))

            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            latency_ms = (time.time() - start_time) * 1000

            result_data = {
                "raw_response": content,
                "content": content
            }

            result = StructuredOutputResult(
                success=True,
                data=result_data,
                method=method_name,
                latency_ms=latency_ms
            )

            self._save_exchange_to_history(session_id, query, result, history_manager)
            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            result = StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method=method_name,
                latency_ms=latency_ms
            )

            return result

    async def method_bind_tools_stream(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto",
        history_manager: SessionHistoryManager = None
    ) -> StructuredOutputResult:
        """方法3: bind_tools + 流式调用

        注意: 此方法使用 tool_call，禁止使用传入的 system_prompt，仅使用简单的 tool_call 系统提示词
        """
        start_time = time.time()
        method_name = "bind_tools_stream"

        tool_call_system_prompt = "You are a helpful assistant that can use tools to complete tasks."

        try:
            llm = self._create_llm()
            lc_tools = [convert_to_openai_tool(t) for t in tools]
            llm_with_tools = llm.bind_tools(lc_tools, tool_choice="auto")
            messages = self._build_messages_with_history(
                query, tool_call_system_prompt, session_id, memory_rounds, history_manager
            )

            full_response = None
            async for chunk in llm_with_tools.astream(messages):
                full_response = chunk

            latency_ms = (time.time() - start_time) * 1000

            if full_response and hasattr(full_response, 'tool_calls') and full_response.tool_calls:
                tool_call = full_response.tool_calls[0]
                # 处理不同格式的 tool_call
                if isinstance(tool_call, dict):
                    # 检查是否是 OpenAI 格式 (function.arguments)
                    if "function" in tool_call:
                        function_data = tool_call["function"]
                        args_str = function_data.get("arguments", "{}")
                        try:
                            import json
                            args = json.loads(args_str) if isinstance(args_str, str) else args_str
                        except json.JSONDecodeError:
                            args = {}
                    else:
                        # LangChain 格式 (args)
                        args = tool_call.get("args", {})
                else:
                    # 对象格式
                    args = getattr(tool_call, 'args', {})
                
                result = StructuredOutputResult(
                    success=True,
                    data=args,
                    method=method_name,
                    latency_ms=latency_ms
                )

                self._save_exchange_to_history(session_id, query, result, history_manager)
                return result

            result = StructuredOutputResult(
                success=False,
                error="No tool calls in stream response",
                method=method_name,
                latency_ms=latency_ms
            )

            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            result = StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method=method_name,
                latency_ms=latency_ms
            )

            return result

    async def method_custom_fc_non_stream(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto",
        history_manager: SessionHistoryManager = None
    ) -> StructuredOutputResult:
        """方法4: 自定义 Function Calling + 非流式

        注意: 此方法使用 tool_call，禁止使用传入的 system_prompt，仅使用简单的 tool_call 系统提示词
        """
        start_time = time.time()
        method_name = "custom_fc_non_stream"

        tool_call_system_prompt = "You are a helpful assistant that can use tools to complete tasks."

        try:
            llm = self._create_llm()
            messages = self._build_messages_with_history(
                query, tool_call_system_prompt, session_id, memory_rounds, history_manager
            )

            tool_definitions = []
            for tool in tools:
                if "function" in tool:
                    tool_definitions.append(tool["function"])
                else:
                    tool_definitions.append(tool)

            client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

            request_messages = [{"role": "system", "content": tool_call_system_prompt}] + \
                        [{"role": m.type, "content": m.content} for m in messages if hasattr(m, 'type')]
            request_tools = [{"type": "function", "function": t} for t in tool_definitions]
            request_tool_choice = "auto" if tool_choice == "auto" else {"type": "function", "function": {"name": tool_choice}}

            response = await client.chat.completions.create(
                model=self.model_name,
                messages=request_messages,
                tools=request_tools,
                tool_choice=request_tool_choice,
                temperature=0.0
            )

            latency_ms = (time.time() - start_time) * 1000

            if response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                args = json.loads(tool_call.function.arguments)
                result = StructuredOutputResult(
                    success=True,
                    data=args,
                    method=method_name,
                    latency_ms=latency_ms
                )

                self._save_exchange_to_history(session_id, query, result, history_manager)
                return result

            result = StructuredOutputResult(
                success=False,
                error="No tool calls in response",
                method=method_name,
                latency_ms=latency_ms
            )

            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            result = StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method=method_name,
                latency_ms=latency_ms
            )

            return result

    async def method_custom_fc_stream(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto",
        history_manager: SessionHistoryManager = None
    ) -> StructuredOutputResult:
        """方法5: 自定义 Function Calling + 流式

        注意: 此方法使用 tool_call，禁止使用传入的 system_prompt，仅使用简单的 tool_call 系统提示词
        """
        start_time = time.time()
        method_name = "custom_fc_stream"

        tool_call_system_prompt = "You are a helpful assistant that can use tools to complete tasks."

        try:
            tool_definitions = []
            for tool in tools:
                if "function" in tool:
                    tool_definitions.append(tool["function"])
                else:
                    tool_definitions.append(tool)

            client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

            messages = [{"role": "system", "content": tool_call_system_prompt}]
            if session_id and history_manager:
                history_manager.trim_history(session_id, memory_rounds)
                history = history_manager.get_history(session_id)
                for msg in history.messages:
                    if isinstance(msg, HumanMessage):
                        messages.append({"role": "user", "content": msg.content})
                    elif isinstance(msg, AIMessage):
                        messages.append({"role": "assistant", "content": msg.content})
            messages.append({"role": "user", "content": query})

            response = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=[{"type": "function", "function": t} for t in tool_definitions],
                tool_choice="auto" if tool_choice == "auto" else {"type": "function", "function": {"name": tool_choice}},
                temperature=0.0,
                stream=True
            )

            tool_calls_data = {}
            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    pass
                if delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        index = tool_call.index
                        if index not in tool_calls_data:
                            tool_calls_data[index] = {"id": "", "function": {"name": "", "arguments": ""}}
                        if tool_call.id:
                            tool_calls_data[index]["id"] = tool_call.id
                        if tool_call.function:
                            if tool_call.function.name:
                                tool_calls_data[index]["function"]["name"] = tool_call.function.name
                            if tool_call.function.arguments:
                                tool_calls_data[index]["function"]["arguments"] += tool_call.function.arguments

            latency_ms = (time.time() - start_time) * 1000

            if tool_calls_data:
                first_tool_call = tool_calls_data[0]
                try:
                    args = json.loads(first_tool_call["function"]["arguments"])
                    result = StructuredOutputResult(
                        success=True,
                        data=args,
                        method=method_name,
                        latency_ms=latency_ms
                    )

                    self._save_exchange_to_history(session_id, query, result, history_manager)
                    return result
                except json.JSONDecodeError as e:
                    result = StructuredOutputResult(
                        success=False,
                        error=f"Failed to parse tool call arguments: {e}",
                        method=method_name,
                        latency_ms=latency_ms
                    )

                    return result

            result = StructuredOutputResult(
                success=False,
                error="No tool calls in stream response",
                method=method_name,
                latency_ms=latency_ms
            )

            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            result = StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method=method_name,
                latency_ms=latency_ms
            )

            return result

    async def method_pydantic_parser(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto",
        history_manager: SessionHistoryManager = None
    ) -> StructuredOutputResult:
        """方法6: PydanticOutputParser - 使用 FC Schema 反向生成 Pydantic 模型

        架构: FC Schema → 反向生成 Pydantic 动态模型
        注意: 此方法不使用 tool_call，系统提示词仅使用传参的 system_prompt
        """
        start_time = time.time()
        method_name = "pydantic_parser"

        try:
            llm = self._create_llm()

            # 使用第一个 tool 的 schema 构建 pydantic_model（后续解析需要）
            fc_schema = tools[0] if tools else {}
            pydantic_model = FCSchemaBuilder.build_pydantic_model_from_fc(fc_schema)
            logger.info(f"[method_pydantic_parser] pydantic_model schema: {pydantic_model.model_json_schema()}")
            parser = PydanticOutputParser(pydantic_object=pydantic_model)

            messages = []
            if system_prompt:
                # 如果传入了 system_prompt（已经是完整的 full_system_prompt），直接使用
                messages.append(SystemMessage(content=system_prompt))
            else:
                messages.append(SystemMessage(content=parser.get_format_instructions()))

            if session_id and history_manager:
                history_manager.trim_history(session_id, memory_rounds)
                history = history_manager.get_history(session_id)
                messages.extend(history.messages)

            messages.append(HumanMessage(content=query))

            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)
            logger.debug(f"[method_pydantic_parser] LLM response content: {content}")

            try:
                parsed_result = parser.parse(content)
                parsed_data = parsed_result.model_dump()
                logger.debug(f"[method_pydantic_parser] parsed_data: {json.dumps(parsed_data, ensure_ascii=False)}")
            except Exception as parse_error:
                logger.error(f"[method_pydantic_parser] parse_error: {parse_error}")
                logger.error(f"[method_pydantic_parser] content that failed to parse: {content}")
                latency_ms = (time.time() - start_time) * 1000
                result = StructuredOutputResult(
                    success=False,
                    error=f"Pydantic parse error: {parse_error}",
                    method=method_name,
                    latency_ms=latency_ms
                )
                return result

            latency_ms = (time.time() - start_time) * 1000

            result = StructuredOutputResult(
                success=True,
                data=parsed_data,
                method=method_name,
                latency_ms=latency_ms
            )

            self._save_exchange_to_history(session_id, query, result, history_manager)
            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            result = StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method=method_name,
                latency_ms=latency_ms
            )

            return result

    async def method_json_parser(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto",
        history_manager: SessionHistoryManager = None
    ) -> StructuredOutputResult:
        """方法7: JsonParser - 使用 FC Schema + JsonOutputParser

        架构: FC Schema → 反向生成 JSON 动态提示词 → JsonOutputParser 解析
        注意: 此方法不使用 tool_call，系统提示词仅使用传参的 system_prompt
        """
        start_time = time.time()
        method_name = "json_parser"

        try:
            llm = self._create_llm()

            parser = JsonOutputParser()

            messages = []
            if system_prompt:
                # 如果传入了 system_prompt（已经是完整的 full_system_prompt），直接使用
                messages.append(SystemMessage(content=system_prompt))
            else:
                # 只有在没有传入 system_prompt 时才构建 json_format_prompt
                fc_schema = tools[0] if tools else {}
                json_format_prompt = FCSchemaBuilder.build_json_prompt_from_fc(fc_schema)
                messages.append(SystemMessage(content=f"{json_format_prompt}\n\n{parser.get_format_instructions()}"))

            if session_id and history_manager:
                history_manager.trim_history(session_id, memory_rounds)
                history = history_manager.get_history(session_id)
                messages.extend(history.messages)

            messages.append(HumanMessage(content=query))

            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            try:
                parsed_data = parser.parse(content)
            except Exception as parse_error:
                latency_ms = (time.time() - start_time) * 1000
                result = StructuredOutputResult(
                    success=False,
                    error=f"JSON parse error: {parse_error}",
                    method=method_name,
                    latency_ms=latency_ms
                )
                return result

            latency_ms = (time.time() - start_time) * 1000

            result = StructuredOutputResult(
                success=True,
                data=parsed_data,
                method=method_name,
                latency_ms=latency_ms
            )

            self._save_exchange_to_history(session_id, query, result, history_manager)
            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            result = StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method=method_name,
                latency_ms=latency_ms
            )

            return result
