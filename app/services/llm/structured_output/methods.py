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

            # 解析第一个 tool_call 的参数
            if tool_calls_data:
                first_tool_call = tool_calls_data[0]
                try:
                    args = json.loads(first_tool_call["function"]["arguments"])
                    result = StructuredOutputResult(
                        success=True,
                        data=args,
                        method="custom_fc_stream"
                    )
                    self._save_exchange_to_history(session_id, query, result, history_manager)
                    return result
                except json.JSONDecodeError as e:
                    return StructuredOutputResult(
                        success=False,
                        error=f"Failed to parse tool call arguments: {e}",
                        method="custom_fc_stream"
                    )

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
        """方法6: PydanticOutputParser - 增强版，确保提取所有字段"""
        try:
            llm = self._create_llm()
            DynamicModel = create_dynamic_model(tools)
            parser = PydanticOutputParser(pydantic_object=DynamicModel)

            # 获取字段定义
            first_tool = tools[0] if tools else {}
            if "function" in first_tool:
                function_def = first_tool.get("function", {})
            else:
                function_def = first_tool
            parameters = function_def.get("parameters", {})
            properties = parameters.get("properties", {})
            required_fields = parameters.get("required", [])

            # 构建详细的字段描述
            fields_desc = []
            for field_name, field_info in properties.items():
                desc = field_info.get("description", "")
                enum = field_info.get("enum", [])
                is_required = field_name in required_fields
                required_mark = " (必填)" if is_required else ""
                if enum:
                    fields_desc.append(f"  - {field_name}{required_mark}: {desc} (可选值: {', '.join(enum)})")
                else:
                    fields_desc.append(f"  - {field_name}{required_mark}: {desc}")

            format_instructions = parser.get_format_instructions()

            # 增强版系统提示词
            full_system_prompt = f"""{system_prompt or ''}

你需要从对话中提取以下字段信息：
{chr(10).join(fields_desc)}

提取要求：
1. 仔细阅读对话内容，提取每个字段的具体值
2. 对于下拉选择字段，从可选值中选择最匹配的
3. 如果某个字段在对话中没有明确信息，设置为null
4. 必须返回所有字段，不能遗漏

输出格式要求：
{format_instructions}

重要提示：
1. 只返回JSON格式的数据，不要返回任何其他文本
2. 不要添加解释、问候或任何其他内容
3. 确保返回的是有效的JSON格式
4. 必须包含所有字段，即使没有明确信息也要设置为null
"""
            messages = self._build_messages_with_history(
                query, full_system_prompt, session_id, memory_rounds, history_manager
            )

            # 添加强制JSON输出的用户提示
            messages.append({"role": "user", "content": "请只返回JSON格式的字段数据，确保包含所有字段，不要添加任何其他文本。"})

            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            # 尝试解析JSON
            parsed_data = None
            try:
                parsed = parser.parse(content)
                parsed_data = parsed.model_dump()
            except Exception:
                # 尝试从内容中提取JSON
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    try:
                        json_str = json_match.group(0)
                        parsed_data = json.loads(json_str)
                    except:
                        pass

            if parsed_data is None:
                return StructuredOutputResult(
                    success=False,
                    error=f"Failed to parse JSON from response",
                    method="pydantic_parser"
                )

            # 确保所有字段都存在（补全缺失字段为null）
            for field_name in properties.keys():
                if field_name not in parsed_data:
                    parsed_data[field_name] = None

            result = StructuredOutputResult(
                success=True,
                data=parsed_data,
                method="pydantic_parser"
            )
            self._save_exchange_to_history(session_id, query, result, history_manager)
            return result

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
        """方法7: JsonOutputParser - 增强版，确保返回扁平结构"""
        try:
            llm = self._create_llm()
            parser = JsonOutputParser()

            # 获取第一个工具的参数定义
            first_tool = tools[0] if tools else {}
            if "function" in first_tool:
                function_def = first_tool.get("function", {})
            else:
                function_def = first_tool
            parameters = function_def.get("parameters", {})
            properties = parameters.get("properties", {})

            # 构建字段描述
            fields_desc = []
            for field_name, field_info in properties.items():
                desc = field_info.get("description", "")
                enum = field_info.get("enum", [])
                if enum:
                    fields_desc.append(f"  - {field_name}: {desc} (可选值: {', '.join(enum)})")
                else:
                    fields_desc.append(f"  - {field_name}: {desc}")

            full_system_prompt = f"""{system_prompt or ''}

你需要从对话中提取以下字段信息，并以JSON格式返回：
{chr(10).join(fields_desc)}

重要要求：
1. 直接返回包含字段的JSON对象，不要嵌套在"fill_form"或其他键下
2. 示例格式：{{"字段名1": "值1", "字段名2": "值2"}}
3. 只返回JSON，不要添加任何解释或markdown格式
4. 如果某个字段没有明确信息，设置为null

{parser.get_format_instructions()}
"""
            messages = self._build_messages_with_history(
                query, full_system_prompt, session_id, memory_rounds, history_manager
            )

            # 添加强制JSON输出的用户提示
            messages.append({"role": "user", "content": "请直接返回JSON格式的字段数据，不要嵌套在fill_form中，不要添加任何其他文本。"})

            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            # 解析JSON数据
            parsed_data = None

            try:
                parsed = parser.parse(content)
                parsed_data = parsed
            except Exception:
                # 尝试直接解析 JSON
                json_content = content
                if "```json" in json_content:
                    json_content = json_content.split("```json")[1].split("```")[0]
                elif "```" in json_content:
                    json_content = json_content.split("```")[1].split("```")[0]

                parsed_data = json.loads(json_content.strip())

            # 处理嵌套结构：如果包含 fill_form 键，提取其值
            if isinstance(parsed_data, dict) and "fill_form" in parsed_data:
                parsed_data = parsed_data["fill_form"]

            result = StructuredOutputResult(
                success=True,
                data=parsed_data,
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
