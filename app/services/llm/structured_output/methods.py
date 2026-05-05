"""
结构化输出方法实现
"""
import json
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_core.output_parsers import PydanticOutputParser, JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_openai import ChatOpenAI

from app.log import logger
from app.services.llm.structured_output.history_manager import SessionHistoryManager
from app.services.llm.structured_output.result import StructuredOutputResult
from app.services.llm.structured_output.utils import (
    build_tools_description,
    create_dynamic_model,
    parse_text_function_call,
)


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
        """方法1: with_structured_output - LangChain 官方结构化输出"""
        try:
            llm = self._create_llm()
            DynamicModel = create_dynamic_model(tools)
            structured_llm = llm.with_structured_output(DynamicModel)
            messages = self._build_messages_with_history(
                query, system_prompt, session_id, memory_rounds, history_manager
            )
            result_data = await structured_llm.ainvoke(messages)

            result = StructuredOutputResult(
                success=True,
                data=result_data.model_dump(),
                method="with_structured_output"
            )
            self._save_exchange_to_history(session_id, query, result, history_manager)
            return result

        except Exception as e:
            return StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method="with_structured_output"
            )

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
        """方法2: bind_tools + 非流式调用"""
        try:
            llm = self._create_llm()
            lc_tools = [convert_to_openai_tool(t) for t in tools]
            llm_with_tools = llm.bind_tools(lc_tools, tool_choice="auto")
            messages = self._build_messages_with_history(
                query, system_prompt, session_id, memory_rounds, history_manager
            )
            response = await llm_with_tools.ainvoke(messages)

            if hasattr(response, 'tool_calls') and response.tool_calls:
                tool_call = response.tool_calls[0]
                args = tool_call.get("args", {})
                result = StructuredOutputResult(
                    success=True,
                    data=args,
                    method="bind_tools_non_stream"
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
                        method="bind_tools_non_stream"
                    )
                    self._save_exchange_to_history(session_id, query, result, history_manager)
                    return result

                return StructuredOutputResult(
                    success=False,
                    error="No tool calls in response",
                    method="bind_tools_non_stream"
                )

        except Exception as e:
            return StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method="bind_tools_non_stream"
            )

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
        """方法3: bind_tools + 流式调用"""
        try:
            llm = self._create_llm()
            lc_tools = [convert_to_openai_tool(t) for t in tools]
            llm_with_tools = llm.bind_tools(lc_tools, tool_choice="auto")
            messages = self._build_messages_with_history(
                query, system_prompt, session_id, memory_rounds, history_manager
            )

            full_response = None
            async for chunk in llm_with_tools.astream(messages):
                full_response = chunk

            if full_response and hasattr(full_response, 'tool_calls') and full_response.tool_calls:
                tool_call = full_response.tool_calls[0]
                args = tool_call.get("args", {})
                result = StructuredOutputResult(
                    success=True,
                    data=args,
                    method="bind_tools_stream"
                )
                self._save_exchange_to_history(session_id, query, result, history_manager)
                return result

            return StructuredOutputResult(
                success=False,
                error="No tool calls in stream response",
                method="bind_tools_stream"
            )

        except Exception as e:
            return StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method="bind_tools_stream"
            )

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
        """方法4: 自定义 Function Calling + 非流式"""
        try:
            llm = self._create_llm()
            messages = self._build_messages_with_history(
                query, system_prompt, session_id, memory_rounds, history_manager
            )

            tool_definitions = []
            for tool in tools:
                if "function" in tool:
                    tool_definitions.append(tool["function"])
                else:
                    tool_definitions.append(tool)

            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

            response = await client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "system", "content": system_prompt or ""}] +
                        [{"role": m.type, "content": m.content} for m in messages if hasattr(m, 'type')],
                tools=[{"type": "function", "function": t} for t in tool_definitions],
                tool_choice="auto" if tool_choice == "auto" else {"type": "function", "function": {"name": tool_choice}},
                temperature=0.0
            )

            if response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                import json
                args = json.loads(tool_call.function.arguments)
                result = StructuredOutputResult(
                    success=True,
                    data=args,
                    method="custom_fc_non_stream"
                )
                self._save_exchange_to_history(session_id, query, result, history_manager)
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
        """方法5: 自定义 Function Calling + 流式"""
        try:
            tool_definitions = []
            for tool in tools:
                if "function" in tool:
                    tool_definitions.append(tool["function"])
                else:
                    tool_definitions.append(tool)

            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

            messages = [{"role": "system", "content": system_prompt or ""}]
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

            full_content = ""
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    full_content += chunk.choices[0].delta.content

            return StructuredOutputResult(
                success=True,
                data={"content": full_content},
                method="custom_fc_stream"
            )

        except Exception as e:
            return StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method="custom_fc_stream"
            )

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
        """方法6: PydanticOutputParser"""
        try:
            llm = self._create_llm()
            DynamicModel = create_dynamic_model(tools)
            parser = PydanticOutputParser(pydantic_object=DynamicModel)

            tools_desc = build_tools_description(tools)
            full_system_prompt = f"""{system_prompt or ''}

你需要提取以下信息:
{tools_desc}

{parser.get_format_instructions()}
"""
            messages = self._build_messages_with_history(
                query, full_system_prompt, session_id, memory_rounds, history_manager
            )

            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            try:
                parsed = parser.parse(content)
                result = StructuredOutputResult(
                    success=True,
                    data=parsed.model_dump(),
                    method="pydantic_parser"
                )
                self._save_exchange_to_history(session_id, query, result, history_manager)
                return result
            except Exception as parse_error:
                return StructuredOutputResult(
                    success=False,
                    error=f"Parse error: {parse_error}",
                    method="pydantic_parser"
                )

        except Exception as e:
            return StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method="pydantic_parser"
            )

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
        """方法7: JsonOutputParser"""
        try:
            llm = self._create_llm()
            parser = JsonOutputParser()

            tools_desc = build_tools_description(tools)
            full_system_prompt = f"""{system_prompt or ''}

你需要提取以下信息:
{tools_desc}

请以JSON格式返回结果。
{parser.get_format_instructions()}
"""
            messages = self._build_messages_with_history(
                query, full_system_prompt, session_id, memory_rounds, history_manager
            )

            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            try:
                parsed = parser.parse(content)
                result = StructuredOutputResult(
                    success=True,
                    data=parsed,
                    method="json_parser"
                )
                self._save_exchange_to_history(session_id, query, result, history_manager)
                return result
            except Exception as parse_error:
                # 尝试直接解析 JSON
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
                self._save_exchange_to_history(session_id, query, result, history_manager)
                return result

        except Exception as e:
            return StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method="json_parser"
            )
