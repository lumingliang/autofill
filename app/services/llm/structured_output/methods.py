"""
结构化输出方法实现
"""
import json
import re
import time
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI

from app.log import logger
from app.services.llm.structured_output.history_manager import SessionHistoryManager
from app.services.llm.structured_output.result import StructuredOutputResult
from app.services.llm.structured_output.utils import (
    create_dynamic_model,
    parse_text_function_call,
)


def log_llm_call(
    method_name: str,
    model_name: str,
    input_data: Dict,
    output_data: Dict,
    latency_ms: float,
    raw_request: Dict = None,
    raw_response: Any = None
):
    """
    记录LLM调用日志

    Args:
        method_name: 方法名称
        model_name: 模型名称
        input_data: 输入数据（包含query, tools, system_prompt等）
        output_data: 输出数据（包含success, data, error等）
        latency_ms: 响应时间（毫秒）
        raw_request: 原始请求参数（发送给大模型的完整参数）
        raw_response: 原始响应（大模型返回的完整响应对象）
    """
    # 处理原始响应，转换为可序列化的格式
    raw_response_dict = None
    if raw_response is not None:
        try:
            if hasattr(raw_response, 'model_dump'):
                raw_response_dict = raw_response.model_dump()
            elif hasattr(raw_response, 'dict'):
                raw_response_dict = raw_response.dict()
            elif hasattr(raw_response, '__dict__'):
                raw_response_dict = raw_response.__dict__
            else:
                raw_response_dict = str(raw_response)
        except Exception as e:
            raw_response_dict = f"<无法序列化: {e}>"

    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "method": method_name,
        "model": model_name,
        "latency_ms": round(latency_ms, 2),
        "input": input_data,
        "output": output_data,
        "raw_request": raw_request,
        "raw_response": raw_response_dict
    }

    # 记录到结构化日志
    logger.info(
        f"[LLM_CALL] {method_name} | model={model_name} | latency={latency_ms:.2f}ms | "
        f"success={output_data.get('success', False)}",
        extra={
            "llm_method": method_name,
            "llm_model": model_name,
            "llm_latency_ms": latency_ms,
            "llm_input": input_data,
            "llm_output": output_data,
            "llm_raw_request": raw_request,
            "llm_raw_response": raw_response_dict
        }
    )

    # 同时记录详细JSON到debug日志
    logger.debug(f"[LLM_CALL_DETAIL] {json.dumps(log_entry, ensure_ascii=False, default=str)}")


class StructuredOutputMethods:
    """结构化输出方法集合"""

    def __init__(self, model_name: str, api_key: str, base_url: str, timeout: int = 60):
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

        # 使用简单的 tool_call 系统提示词，禁止使用传入的 system_prompt
        tool_call_system_prompt = "You are a helpful assistant that can use tools to complete tasks."

        # 记录输入参数
        input_data = {
            "query": query,
            "tools_count": len(tools),
            "tools": tools,
            "system_prompt": system_prompt,
            "actual_system_prompt": tool_call_system_prompt,
            "session_id": session_id,
            "memory_rounds": memory_rounds,
            "tool_choice": tool_choice
        }

        try:
            llm = self._create_llm()
            DynamicModel = create_dynamic_model(tools)
            structured_llm = llm.with_structured_output(DynamicModel)
            messages = self._build_messages_with_history(
                query, tool_call_system_prompt, session_id, memory_rounds, history_manager
            )

            # 记录原始请求参数
            raw_request = {
                "model": self.model_name,
                "messages": [{"role": m.type, "content": m.content} for m in messages if hasattr(m, 'type')],
                "tools": tools,
                "tool_choice": tool_choice,
                "temperature": 0.0
            }

            result_data = await structured_llm.ainvoke(messages)

            latency_ms = (time.time() - start_time) * 1000

            result = StructuredOutputResult(
                success=True,
                data=result_data.model_dump(),
                method=method_name,
                latency_ms=latency_ms
            )

            # 记录输出
            output_data = {
                "success": True,
                "data": result_data.model_dump(),
                "method": method_name
            }
            log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request, result_data)

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

            # 记录错误输出
            output_data = {
                "success": False,
                "error": f"{type(e).__name__}: {e}",
                "method": method_name
            }
            log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request if 'raw_request' in locals() else None, None)

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

        # 使用简单的 tool_call 系统提示词，禁止使用传入的 system_prompt
        tool_call_system_prompt = "You are a helpful assistant that can use tools to complete tasks."

        input_data = {
            "query": query,
            "tools_count": len(tools),
            "tools": tools,
            "system_prompt": system_prompt,
            "actual_system_prompt": tool_call_system_prompt,
            "session_id": session_id,
            "memory_rounds": memory_rounds,
            "tool_choice": tool_choice
        }

        try:
            llm = self._create_llm()
            lc_tools = [convert_to_openai_tool(t) for t in tools]
            llm_with_tools = llm.bind_tools(lc_tools, tool_choice="auto")
            messages = self._build_messages_with_history(
                query, tool_call_system_prompt, session_id, memory_rounds, history_manager
            )

            # 记录原始请求参数
            raw_request = {
                "model": self.model_name,
                "messages": [{"role": m.type, "content": m.content} for m in messages if hasattr(m, 'type')],
                "tools": lc_tools,
                "tool_choice": "auto",
                "temperature": 0.0
            }

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

                output_data = {"success": True, "data": args, "method": method_name}
                log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request, response)

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

                    output_data = {"success": True, "data": parsed_args, "method": method_name}
                    log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request, response)

                    self._save_exchange_to_history(session_id, query, result, history_manager)
                    return result

                result = StructuredOutputResult(
                    success=False,
                    error="No tool calls in response",
                    method=method_name,
                    latency_ms=latency_ms
                )

                output_data = {"success": False, "error": "No tool calls in response", "method": method_name}
                log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request, response)

                return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            result = StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method=method_name,
                latency_ms=latency_ms
            )

            output_data = {"success": False, "error": f"{type(e).__name__}: {e}", "method": method_name}
            log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request if 'raw_request' in locals() else None, None)

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

        input_data = {
            "query": query,
            "system_prompt": system_prompt,
            "session_id": session_id,
            "memory_rounds": memory_rounds,
            "note": "纯文本模式，直接返回原始响应"
        }

        try:
            llm = self._create_llm()

            # 构建消息列表
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))

            if session_id and history_manager:
                history_manager.trim_history(session_id, memory_rounds)
                history = history_manager.get_history(session_id)
                messages.extend(history.messages)

            messages.append(HumanMessage(content=query))

            # 记录原始请求参数
            raw_request = {
                "model": self.model_name,
                "messages": [{"role": m.type, "content": m.content} for m in messages if hasattr(m, 'type')],
                "temperature": 0.0
            }

            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            latency_ms = (time.time() - start_time) * 1000

            # 构建原始响应数据
            raw_response_data = {
                "content": content
            }

            # 构建结果数据
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

            output_data = {"success": True, "data": result_data, "method": method_name}
            log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request, raw_response_data)

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

            output_data = {"success": False, "error": f"{type(e).__name__}: {e}", "method": method_name}
            log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request if 'raw_request' in locals() else None, None)

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

        # 使用简单的 tool_call 系统提示词，禁止使用传入的 system_prompt
        tool_call_system_prompt = "You are a helpful assistant that can use tools to complete tasks."

        input_data = {
            "query": query,
            "tools_count": len(tools),
            "tools": tools,
            "system_prompt": system_prompt,
            "actual_system_prompt": tool_call_system_prompt,
            "session_id": session_id,
            "memory_rounds": memory_rounds,
            "tool_choice": tool_choice
        }

        try:
            llm = self._create_llm()
            lc_tools = [convert_to_openai_tool(t) for t in tools]
            llm_with_tools = llm.bind_tools(lc_tools, tool_choice="auto")
            messages = self._build_messages_with_history(
                query, tool_call_system_prompt, session_id, memory_rounds, history_manager
            )

            # 记录原始请求参数
            raw_request = {
                "model": self.model_name,
                "messages": [{"role": m.type, "content": m.content} for m in messages if hasattr(m, 'type')],
                "tools": lc_tools,
                "tool_choice": "auto",
                "temperature": 0.0,
                "stream": True
            }

            full_response = None
            async for chunk in llm_with_tools.astream(messages):
                full_response = chunk

            latency_ms = (time.time() - start_time) * 1000

            if full_response and hasattr(full_response, 'tool_calls') and full_response.tool_calls:
                tool_call = full_response.tool_calls[0]
                args = tool_call.get("args", {})
                result = StructuredOutputResult(
                    success=True,
                    data=args,
                    method=method_name,
                    latency_ms=latency_ms
                )

                output_data = {"success": True, "data": args, "method": method_name}
                log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request, full_response)

                self._save_exchange_to_history(session_id, query, result, history_manager)
                return result

            result = StructuredOutputResult(
                success=False,
                error="No tool calls in stream response",
                method=method_name,
                latency_ms=latency_ms
            )

            output_data = {"success": False, "error": "No tool calls in stream response", "method": method_name}
            log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request, full_response)

            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            result = StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method=method_name,
                latency_ms=latency_ms
            )

            output_data = {"success": False, "error": f"{type(e).__name__}: {e}", "method": method_name}
            log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request if 'raw_request' in locals() else None, None)

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

        # 使用简单的 tool_call 系统提示词，禁止使用传入的 system_prompt
        tool_call_system_prompt = "You are a helpful assistant that can use tools to complete tasks."

        input_data = {
            "query": query,
            "tools_count": len(tools),
            "tools": tools,
            "system_prompt": system_prompt,
            "actual_system_prompt": tool_call_system_prompt,
            "session_id": session_id,
            "memory_rounds": memory_rounds,
            "tool_choice": tool_choice
        }

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

            # 记录原始请求参数
            raw_request = {
                "model": self.model_name,
                "messages": [{"role": "system", "content": tool_call_system_prompt}] +
                            [{"role": m.type, "content": m.content} for m in messages if hasattr(m, 'type')],
                "tools": [{"type": "function", "function": t} for t in tool_definitions],
                "tool_choice": "auto" if tool_choice == "auto" else {"type": "function", "function": {"name": tool_choice}},
                "temperature": 0.0
            }

            response = await client.chat.completions.create(
                model=self.model_name,
                messages=raw_request["messages"],
                tools=raw_request["tools"],
                tool_choice=raw_request["tool_choice"],
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

                output_data = {"success": True, "data": args, "method": method_name}
                log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request, response)

                self._save_exchange_to_history(session_id, query, result, history_manager)
                return result

            result = StructuredOutputResult(
                success=False,
                error="No tool calls in response",
                method=method_name,
                latency_ms=latency_ms
            )

            output_data = {"success": False, "error": "No tool calls in response", "method": method_name}
            log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request, response)

            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            result = StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method=method_name,
                latency_ms=latency_ms
            )

            output_data = {"success": False, "error": f"{type(e).__name__}: {e}", "method": method_name}
            log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request if 'raw_request' in locals() else None, None)

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

        # 使用简单的 tool_call 系统提示词，禁止使用传入的 system_prompt
        tool_call_system_prompt = "You are a helpful assistant that can use tools to complete tasks."

        input_data = {
            "query": query,
            "tools_count": len(tools),
            "tools": tools,
            "system_prompt": system_prompt,
            "actual_system_prompt": tool_call_system_prompt,
            "session_id": session_id,
            "memory_rounds": memory_rounds,
            "tool_choice": tool_choice
        }

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

            # 记录原始请求参数
            raw_request = {
                "model": self.model_name,
                "messages": messages,
                "tools": [{"type": "function", "function": t} for t in tool_definitions],
                "tool_choice": "auto" if tool_choice == "auto" else {"type": "function", "function": {"name": tool_choice}},
                "temperature": 0.0,
                "stream": True
            }

            response = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=[{"type": "function", "function": t} for t in tool_definitions],
                tool_choice="auto" if tool_choice == "auto" else {"type": "function", "function": {"name": tool_choice}},
                temperature=0.0,
                stream=True
            )

            # 收集 tool_calls
            tool_calls_data = {}
            async for chunk in response:
                delta = chunk.choices[0].delta
                # 处理 content
                if delta.content:
                    pass  # 忽略 content，只关注 tool_calls
                # 处理 tool_calls
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

            # 构建原始响应数据（流式响应的聚合结果）
            raw_response_data = {
                "tool_calls": tool_calls_data,
                "stream": True
            }

            # 解析第一个 tool_call 的参数
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

                    output_data = {"success": True, "data": args, "method": method_name}
                    log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request, raw_response_data)

                    self._save_exchange_to_history(session_id, query, result, history_manager)
                    return result
                except json.JSONDecodeError as e:
                    result = StructuredOutputResult(
                        success=False,
                        error=f"Failed to parse tool call arguments: {e}",
                        method=method_name,
                        latency_ms=latency_ms
                    )

                    output_data = {"success": False, "error": f"Failed to parse tool call arguments: {e}", "method": method_name}
                    log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request, raw_response_data)

                    return result

            result = StructuredOutputResult(
                success=False,
                error="No tool calls in stream response",
                method=method_name,
                latency_ms=latency_ms
            )

            output_data = {"success": False, "error": "No tool calls in stream response", "method": method_name}
            log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request, raw_response_data)

            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            result = StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method=method_name,
                latency_ms=latency_ms
            )

            output_data = {"success": False, "error": f"{type(e).__name__}: {e}", "method": method_name}
            log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request if 'raw_request' in locals() else None, None)

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
        """方法6: PydanticOutputParser - 使用简单系统提示词

        注意: 此方法不使用 tool_call，禁止使用 tools 进行参数封装，系统提示词仅使用传参的 system_prompt，禁止拼接 format_instructions
        """
        start_time = time.time()
        method_name = "pydantic_parser"

        input_data = {
            "query": query,
            "system_prompt": system_prompt,
            "session_id": session_id,
            "memory_rounds": memory_rounds,
            "note": "此方法不使用 tools 进行参数封装，仅使用传入的 system_prompt"
        }

        try:
            llm = self._create_llm()

            # 仅使用传入的 system_prompt，禁止拼接 format_instructions
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))

            if session_id and history_manager:
                history_manager.trim_history(session_id, memory_rounds)
                history = history_manager.get_history(session_id)
                messages.extend(history.messages)

            messages.append(HumanMessage(content=query))

            # 记录原始请求参数
            raw_request = {
                "model": self.model_name,
                "messages": [{"role": m.type, "content": m.content} for m in messages if hasattr(m, 'type')],
                "temperature": 0.0
            }

            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            # 尝试解析JSON
            parsed_data = None
            try:
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    json_str = json_match.group(0)
                    parsed_data = json.loads(json_str)
            except Exception:
                pass

            latency_ms = (time.time() - start_time) * 1000

            # 构建原始响应数据
            raw_response_data = {
                "content": content,
                "tool_calls": None
            }

            if parsed_data is None:
                result = StructuredOutputResult(
                    success=False,
                    error=f"Failed to parse JSON from response",
                    method=method_name,
                    latency_ms=latency_ms
                )

                output_data = {"success": False, "error": "Failed to parse JSON from response", "method": method_name}
                log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request, raw_response_data)

                return result

            result = StructuredOutputResult(
                success=True,
                data=parsed_data,
                method=method_name,
                latency_ms=latency_ms
            )

            output_data = {"success": True, "data": parsed_data, "method": method_name}
            log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request, raw_response_data)

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

            output_data = {"success": False, "error": f"{type(e).__name__}: {e}", "method": method_name}
            log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request if 'raw_request' in locals() else None, None)

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
        """方法7: JsonOutputParser - 使用简单系统提示词

        注意: 此方法不使用 tool_call，禁止使用 tools 进行参数封装，系统提示词仅使用传参的 system_prompt，禁止拼接 format_instructions
        """
        start_time = time.time()
        method_name = "json_parser"

        input_data = {
            "query": query,
            "system_prompt": system_prompt,
            "session_id": session_id,
            "memory_rounds": memory_rounds,
            "note": "此方法不使用 tools 进行参数封装，仅使用传入的 system_prompt"
        }

        try:
            llm = self._create_llm()

            # 仅使用传入的 system_prompt，禁止拼接 format_instructions
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))

            if session_id and history_manager:
                history_manager.trim_history(session_id, memory_rounds)
                history = history_manager.get_history(session_id)
                messages.extend(history.messages)

            messages.append(HumanMessage(content=query))

            # 记录原始请求参数
            raw_request = {
                "model": self.model_name,
                "messages": [{"role": m.type, "content": m.content} for m in messages if hasattr(m, 'type')],
                "temperature": 0.0
            }

            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            # 解析JSON数据
            parsed_data = None

            try:
                # 尝试直接解析 JSON
                json_content = content
                if "```json" in json_content:
                    json_content = json_content.split("```json")[1].split("```")[0]
                elif "```" in json_content:
                    json_content = json_content.split("```")[1].split("```")[0]

                parsed_data = json.loads(json_content.strip())
            except Exception:
                pass

            latency_ms = (time.time() - start_time) * 1000

            # 构建原始响应数据
            raw_response_data = {
                "content": content,
                "tool_calls": None
            }

            # 处理嵌套结构：如果包含 fill_form 键，提取其值
            if isinstance(parsed_data, dict) and "fill_form" in parsed_data:
                parsed_data = parsed_data["fill_form"]

            if parsed_data is None:
                result = StructuredOutputResult(
                    success=False,
                    error=f"Failed to parse JSON from response",
                    method=method_name,
                    latency_ms=latency_ms
                )

                output_data = {"success": False, "error": "Failed to parse JSON from response", "method": method_name}
                log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request, raw_response_data)

                return result

            result = StructuredOutputResult(
                success=True,
                data=parsed_data,
                method=method_name,
                latency_ms=latency_ms
            )

            output_data = {"success": True, "data": parsed_data, "method": method_name}
            log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request, raw_response_data)

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

            output_data = {"success": False, "error": f"{type(e).__name__}: {e}", "method": method_name}
            log_llm_call(method_name, self.model_name, input_data, output_data, latency_ms, raw_request if 'raw_request' in locals() else None, None)

            return result
