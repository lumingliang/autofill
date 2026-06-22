"""
AgentLoop - 通用 Agent 执行引擎

负责多轮对话、工具调用、历史管理、流式与非流式响应的通用逻辑。
"""
import asyncio
import json
import platform
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from app.core.ctx import Ctx
from app.log import logger
from app.services.agent.agent_config import AgentConfig
from app.services.agent.conversation_manager import ConversationManager
from app.services.agent.message_builder import EnvInfo, MessageBuilder
from app.services.agent.prompt_renderer import PromptRenderer
from app.services.agent.tool_executor import format_tool_result
from app.services.agent.tool_registry import ToolRegistry


@dataclass
class ToolContext:
    """工具执行上下文"""
    session_id: str
    agent_name: str
    tenant_id: str
    user_id: str
    agent_config: AgentConfig


class AgentLoop:
    """通用 Agent 执行循环"""

    def __init__(
        self,
        config: AgentConfig,
        tools: List[BaseTool],
        llm: ChatOpenAI,
        conversation_manager: ConversationManager,
        prompt_renderer: PromptRenderer,
    ):
        self.config = config
        self.tools = tools
        self.llm = llm
        self.conversation_manager = conversation_manager
        self.prompt_renderer = prompt_renderer

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        variables = dict(self.config.system_prompt_variables)
        variables["agent_name"] = self.config.name
        variables["model_name"] = self.config.model

        return self.prompt_renderer.render(
            sections=self.config.system_prompt_sections,
            separator=self.config.system_prompt_separator,
            variables=variables,
        )

    def _format_user_message(
        self,
        query: str,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        """格式化用户消息"""
        builder = MessageBuilder()

        # 设置环境信息
        env_info = EnvInfo(
            primary_working_directory="/Users/lu/code/code/py/autofill",
            working_directories=["/Users/lu/code/code/py/autofill"],
            operating_system=platform.system().lower(),
            today_date=datetime.now().strftime("%Y-%m-%d"),
            knowledge_cutoff="August 2025",
            model_name=self.config.model
        )
        builder.set_env_info(env_info)

        # 按 Agent 配置启用 reminder
        mb_opts = self.config.message_builder_options
        if mb_opts.get("enable_skill_reminder", False):
            builder.enable_skill_reminder()
        if mb_opts.get("enable_language_settings", False):
            builder.enable_language_settings()

        # 可选：在用户消息中再次提醒可用工具
        if mb_opts.get("enable_tool_reminder", False):
            builder.enable_tool_reminder()

        return builder.build_user_message(query, inputs=inputs)

    def _log_context(self, session_id: str, event: str, extra: Optional[Dict[str, Any]] = None):
        """打印带标签的日志"""
        data = {
            "event": event,
            "agent_name": self.config.name,
            "session_id": session_id,
        }
        if extra:
            data.update(extra)
        logger.info(data)

    async def _execute_tool(
        self,
        tool_call: Dict[str, Any],
        tool_context: ToolContext,
    ) -> ToolMessage:
        """执行单个工具调用并返回 ToolMessage"""
        tool_name = tool_call["name"]
        tool_args = tool_call.get("args", {})
        tool_id = tool_call.get("id", "call_unknown")

        # 查找工具
        target_tool = None
        for tool in self.tools:
            if tool.name == tool_name:
                target_tool = tool
                break

        if target_tool is None:
            error_msg = format_tool_result("error", {"error": f"Unknown tool: {tool_name}"})
            return ToolMessage(content=error_msg, tool_call_id=tool_id, name=tool_name)

        try:
            # 构建 RunnableConfig 传递上下文
            config = RunnableConfig(metadata={"tool_context": tool_context})
            result = await target_tool.ainvoke(tool_args, config=config)
            return ToolMessage(content=str(result), tool_call_id=tool_id, name=tool_name)
        except Exception as e:
            error_msg = format_tool_result("error", {"error": f"Tool execution failed: {str(e)}"})
            return ToolMessage(content=error_msg, tool_call_id=tool_id, name=tool_name)

    async def _execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        tool_context: ToolContext,
    ) -> List[ToolMessage]:
        """并发执行多个工具调用"""
        tasks = [self._execute_tool(tc, tool_context) for tc in tool_calls]
        return await asyncio.gather(*tasks)

    async def run(
        self,
        session_id: str,
        query: str,
        user_id: str = "default",
        inputs: Optional[Dict[str, Any]] = None,
        max_iterations: Optional[int] = None,
    ) -> Dict[str, Any]:
        """非流式执行 Agent Loop"""
        tenant_id = str(Ctx.get_effective_tenant_id())
        self._log_context(session_id, "agent_loop_start", {
            "query": query[:200] if query else "",
            "user_id": user_id,
        })

        history = self.conversation_manager.get_messages()

        # 新会话注入系统提示词
        if not history:
            system_prompt = self._build_system_prompt()
            self.conversation_manager.add_message(SystemMessage(content=system_prompt))

        # 添加用户消息
        user_content_parts = self._format_user_message(query, inputs)
        self.conversation_manager.add_message(HumanMessage(content=user_content_parts))

        # 绑定工具
        llm_with_tools = self.llm.bind_tools(self.tools)

        final_response = ""
        tool_calls_executed = []
        finish_reason = "max_iterations"
        last_response: Optional[BaseMessage] = None
        max_iterations = max_iterations if max_iterations is not None else self.config.max_iterations

        for iteration in range(max_iterations):
            self._log_context(session_id, "agent_iteration_start", {
                "iteration": iteration + 1,
                "max_iterations": max_iterations,
                "history_message_count": len(history)
            })

            response = await llm_with_tools.ainvoke(history)
            last_response = response

            self._log_context(session_id, "agent_llm_response", {
                "iteration": iteration + 1,
                "content_preview": response.content[:200] if response.content else "(empty)",
                "has_tool_calls": bool(response.tool_calls),
                "tool_calls_count": len(response.tool_calls) if response.tool_calls else 0,
            })

            if response.tool_calls:
                tool_context = ToolContext(
                    session_id=session_id,
                    agent_name=self.config.name,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    agent_config=self.config,
                )

                tool_messages = await self._execute_tool_calls(response.tool_calls, tool_context)
                self.conversation_manager.add_messages([response, *tool_messages])

                for tc, tm in zip(response.tool_calls, tool_messages):
                    tool_calls_executed.append({
                        "id": tc.get("id", "call_unknown"),
                        "name": tc.get("name", ""),
                        "args": tc.get("args", {}),
                        "result": str(tm.content)[:1000],
                    })

                continue

            self.conversation_manager.add_message(response)
            final_response = response.content
            finish_reason = "stop"
            self._log_context(session_id, "agent_chat_complete", {
                "finish_reason": "stop",
                "iterations_used": iteration + 1
            })
            break

        if finish_reason == "max_iterations":
            logger.warning({
                "event": "agent_max_iterations_reached",
                "agent_name": self.config.name,
                "session_id": session_id,
                "max_iterations": max_iterations
            })

        result = {
            "answer": final_response,
            "session_id": session_id,
            "agent_name": self.config.name,
            "tool_calls": tool_calls_executed,
            "finish_reason": finish_reason
        }

        if last_response and hasattr(last_response, 'reasoning_content') and last_response.reasoning_content:
            result['reasoning_content'] = last_response.reasoning_content

        return result

    async def run_stream(
        self,
        session_id: str,
        query: str,
        user_id: str = "default",
        inputs: Optional[Dict[str, Any]] = None,
        max_iterations: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """流式执行 Agent Loop"""
        tenant_id = str(Ctx.get_effective_tenant_id())
        self._log_context(session_id, "agent_loop_stream_start", {
            "query": query[:200] if query else "",
            "user_id": user_id,
        })

        history = self.conversation_manager.get_messages()

        # 新会话注入系统提示词
        if not history:
            system_prompt = self._build_system_prompt()
            self.conversation_manager.add_message(SystemMessage(content=system_prompt))

        # 添加用户消息
        user_content_parts = self._format_user_message(query, inputs)
        self.conversation_manager.add_message(HumanMessage(content=user_content_parts))

        # 绑定工具
        llm_with_tools = self.llm.bind_tools(self.tools)

        yield f"data: {json.dumps({'type': 'start', 'session_id': session_id, 'agent_name': self.config.name}, ensure_ascii=False)}\n\n"

        max_iterations = max_iterations if max_iterations is not None else self.config.max_iterations
        for iteration in range(max_iterations):
            full_content = ""
            reasoning_content = ""
            ai_chunk_accumulator = None

            async for chunk in llm_with_tools.astream(history):
                if ai_chunk_accumulator is None:
                    ai_chunk_accumulator = chunk
                else:
                    ai_chunk_accumulator = ai_chunk_accumulator + chunk

                if chunk.content:
                    full_content += chunk.content
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk.content}, ensure_ascii=False)}\n\n"

                if hasattr(chunk, 'reasoning_content') and chunk.reasoning_content:
                    reasoning_content += chunk.reasoning_content
                    yield f"data: {json.dumps({'type': 'reasoning', 'content': chunk.reasoning_content}, ensure_ascii=False)}\n\n"

            tool_calls_buffer = []
            if ai_chunk_accumulator and hasattr(ai_chunk_accumulator, 'tool_calls') and ai_chunk_accumulator.tool_calls:
                tool_calls_buffer = ai_chunk_accumulator.tool_calls

            if tool_calls_buffer:
                ai_msg = AIMessage(content=full_content, tool_calls=tool_calls_buffer)
            else:
                ai_msg = AIMessage(content=full_content)

            if tool_calls_buffer:
                yield f"data: {json.dumps({'type': 'tool_start', 'count': len(tool_calls_buffer)}, ensure_ascii=False)}\n\n"

                tool_context = ToolContext(
                    session_id=session_id,
                    agent_name=self.config.name,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    agent_config=self.config,
                )

                tool_messages = await self._execute_tool_calls(tool_calls_buffer, tool_context)
                self.conversation_manager.add_messages([ai_msg, *tool_messages])

                for tc, tm in zip(tool_calls_buffer, tool_messages):
                    tool_name = tc.get("name", "")
                    yield f"data: {json.dumps({'type': 'tool_use', 'name': tool_name, 'arguments': tc.get('args', {})}, ensure_ascii=False)}\n\n"
                    yield f"data: {json.dumps({'type': 'tool_result', 'name': tool_name, 'status': 'success'}, ensure_ascii=False)}\n\n"

                continue

            self.conversation_manager.add_message(ai_msg)

            done_event = {'type': 'done', 'finish_reason': 'stop'}
            if reasoning_content:
                done_event['reasoning_content'] = reasoning_content
            yield f"data: {json.dumps(done_event, ensure_ascii=False)}\n\n"
            break

        else:
            logger.warning({
                "event": "agent_max_iterations_reached",
                "agent_name": self.config.name,
                "session_id": session_id,
                "max_iterations": max_iterations
            })
            yield f"data: {json.dumps({'type': 'done', 'finish_reason': 'max_iterations'}, ensure_ascii=False)}\n\n"
