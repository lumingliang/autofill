"""
Agent 核心模块 - 实现基于 1.json 规范的 Agent 系统

核心功能：
1. 多轮对话管理 - 严格遵循 1.json 消息格式
2. 工具调用和执行
3. Skill 加载（通过工具结果返回）
4. 流式响应

消息格式规范：
- 用户消息使用复合消息数组格式
- system-reminder 在 user_input 前后都有
- Skill 内容通过 tool 结果返回给大模型
"""
import json
import asyncio
import platform
import toml
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, AsyncGenerator, Union, Literal
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
    BaseMessage,
)
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, create_model, Field

from app.services.agent.system_prompt import get_system_prompt
from app.services.agent.tool_definitions import get_tool_definitions
from app.services.agent.tool_executor import execute_tool
from app.services.agent.message_builder import get_message_builder, EnvInfo, TerminalInfo
from app.log import logger


# ==================== 对话上下文管理 ====================

class ConversationManager:
    """对话上下文管理器 - 管理多轮对话历史"""

    def __init__(self, max_history: int = 20):
        self._conversations: Dict[str, List[BaseMessage]] = {}
        self._max_history = max_history

    def get_or_create(self, conversation_id: str) -> List[BaseMessage]:
        """获取或创建对话"""
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []
        return self._conversations[conversation_id]

    def add_message(self, conversation_id: str, message: BaseMessage) -> None:
        """添加消息到对话历史"""
        history = self.get_or_create(conversation_id)
        history.append(message)

        # 限制历史长度
        if len(history) > self._max_history:
            # 保留系统消息和最近的对话
            system_msgs = [m for m in history if isinstance(m, SystemMessage)]
            other_msgs = [m for m in history if not isinstance(m, SystemMessage)]
            other_msgs = other_msgs[-(self._max_history - len(system_msgs)):]
            self._conversations[conversation_id] = system_msgs + other_msgs

    def clear(self, conversation_id: str) -> None:
        """清空对话"""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]


# ==================== Agent 核心类 ====================

class TraeAgent:
    """
    Trae IDE Agent - 基于 1.json 规范实现

    支持：
    - 多轮对话
    - 工具调用
    - Skill 加载
    - 流式响应

    消息格式严格遵循 1.json 规范：
    - 用户消息为复合消息数组
    - system-reminder 包裹 user_input
    - Skill 激活后内容注入上下文
    """

    def __init__(
        self,
        model: str = "qwen3.6-plus-2026-04-02",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_iterations: int = 10,
    ):
        self.model_name = model
        self.max_iterations = max_iterations

        # 初始化 LangChain Chat Model
        self.llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            streaming=True,
        )

        # 对话管理器
        self.conversation_manager = ConversationManager()

        # 工具定义
        self.tool_definitions = get_tool_definitions()

        # 将工具定义转换为 LangChain 工具
        self.langchain_tools = self._create_langchain_tools()

    def _schema_to_type(self, prop_def: dict, model_prefix: str = "") -> type:
        """递归将 JSON Schema 定义转换为 Python/Pydantic 类型"""
        prop_type = prop_def.get("type", "string")

        if prop_type == "string":
            enum_values = prop_def.get("enum")
            if enum_values:
                return Literal[tuple(enum_values)]
            return str
        elif prop_type == "integer":
            return int
        elif prop_type == "number":
            return float
        elif prop_type == "boolean":
            return bool
        elif prop_type == "array":
            items = prop_def.get("items")
            if items and isinstance(items, dict):
                item_type = self._schema_to_type(items, model_prefix=model_prefix + "Item")
                return List[item_type]
            return List
        elif prop_type == "object":
            nested_props = prop_def.get("properties", {})
            if nested_props:
                return self._build_model(
                    f"{model_prefix}Nested" if model_prefix else "NestedModel",
                    nested_props,
                    prop_def.get("required", [])
                )
            return dict
        else:
            return str

    def _build_model(self, model_name: str, properties: dict, required: list) -> type:
        """递归构建 Pydantic 模型"""
        fields = {}
        for prop_name, prop_def in properties.items():
            py_type = self._schema_to_type(prop_def, model_prefix=f"{model_name}_{prop_name}")
            is_required = prop_name in required
            description = prop_def.get("description", "")
            if not is_required:
                py_type = Optional[py_type]
                fields[prop_name] = (py_type, Field(default=None, description=description))
            else:
                fields[prop_name] = (py_type, Field(description=description))
        return create_model(model_name, **fields, __config__={'extra': 'forbid'})

    def _create_langchain_tools(self) -> List[StructuredTool]:
        """创建 LangChain 工具列表"""
        tools = []
        for tool_def in self.tool_definitions:
            func = tool_def["function"]
            tool_name = func["name"]

            # 创建一个包装函数，使用闭包捕获 tool_name
            def create_wrapper(name):
                async def tool_wrapper(**kwargs):
                    logger.debug({
                        "event": "tool_wrapper_received",
                        "tool_name": name,
                        "arguments": kwargs
                    })
                    return await execute_tool(name, kwargs)
                return tool_wrapper

            # 从 Pydantic schema 创建 args_schema
            parameters = func.get("parameters", {})

            # 创建动态 Pydantic 模型作为 args_schema
            if parameters:
                # 提取属性定义
                properties = parameters.get("properties", {})
                required = parameters.get("required", [])

                # 构建字段定义
                fields = {}
                for prop_name, prop_def in properties.items():
                    py_type = self._schema_to_type(prop_def, model_prefix=f"{tool_name}_{prop_name}")
                    is_required = prop_name in required
                    description = prop_def.get("description", "")
                    if not is_required:
                        py_type = Optional[py_type]
                        fields[prop_name] = (py_type, Field(default=None, description=description))
                    else:
                        fields[prop_name] = (py_type, Field(description=description))

                # 创建 Pydantic 模型
                if fields:
                    args_schema = create_model(f"{tool_name}Input", **fields, __config__={'extra': 'forbid'})
                else:
                    args_schema = None
            else:
                args_schema = None

            tool = StructuredTool.from_function(
                name=tool_name,
                description=func["description"],
                func=create_wrapper(tool_name),
                args_schema=args_schema,
                coroutine=create_wrapper(tool_name),
            )
            tools.append(tool)
        return tools

    def _format_user_message(self, query: str, inputs: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """格式化用户消息为 1.json 规范格式

        使用 MessageBuilder 构建复合消息结构，支持多种标签类型。

        Args:
            query: 用户输入内容
            inputs: 额外输入参数

        Returns:
            格式化的消息数组，每个元素是 {"type": "text", "text": "..."}
        """
        builder = get_message_builder()

        # 设置环境信息
        env_info = EnvInfo(
            primary_working_directory="/Users/lu/code/code/py/autofill",
            working_directories=["/Users/lu/code/code/py/autofill"],
            operating_system=platform.system().lower(),
            today_date=datetime.now().strftime("%Y-%m-%d"),
            knowledge_cutoff="August 2025",
            model_name=self.model_name
        )
        builder.set_env_info(env_info)

        # 启用 Skill 触发提醒
        builder.enable_skill_reminder()

        # 启用语言设置提醒
        builder.enable_language_settings()

        # 构建用户消息
        return builder.build_user_message(query, inputs=inputs)



    async def chat(
        self,
        query: str,
        conversation_id: str,
        user_id: str = "default",
        inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """执行对话 - 自动决策是否调用工具

        流程：
        1. 构建系统提示词
        2. 添加用户消息到上下文（严格遵循 1.json 格式）
        3. 循环调用 LLM，直到 finish_reason="stop" 或达到最大迭代次数
        4. 如果返回 tool_calls，执行工具并继续
        5. 如果是 Skill 工具，注入 Skill 内容到上下文
        6. 返回最终结果

        Args:
            query: 用户输入
            conversation_id: 对话ID
            user_id: 用户ID
            inputs: 额外输入参数

        Returns:
            包含 answer, tool_calls, finish_reason 的结果字典
        """
        # 获取或创建对话历史
        history = self.conversation_manager.get_or_create(conversation_id)

        # 如果是新对话，添加系统提示词
        if not history:
            system_prompt = get_system_prompt()
            history.append(SystemMessage(content=system_prompt))

        # 添加用户消息（严格遵循 1.json 格式 - content 为数组）
        user_content_parts = self._format_user_message(query, inputs)
        history.append(HumanMessage(content=user_content_parts))

        # 绑定工具到 LLM
        llm_with_tools = self.llm.bind_tools(self.langchain_tools)

        # 多轮对话循环
        final_response = ""
        tool_calls_executed = []
        finish_reason = "max_iterations"

        for iteration in range(self.max_iterations):
            logger.debug({
                "event": "agent_iteration_start",
                "conversation_id": conversation_id,
                "iteration": iteration + 1,
                "max_iterations": self.max_iterations,
                "history_message_count": len(history)
            })

            # 调用 LLM
            response = await llm_with_tools.ainvoke(history)

            # 记录 LLM 返回信息
            logger.debug({
                "event": "agent_llm_response",
                "conversation_id": conversation_id,
                "iteration": iteration + 1,
                "content_preview": response.content[:200] if response.content else "(empty)",
                "has_tool_calls": bool(response.tool_calls),
                "tool_calls_count": len(response.tool_calls) if response.tool_calls else 0,
                "tool_calls": [{"name": tc.get("name"), "args": tc.get("args")} for tc in response.tool_calls] if response.tool_calls else []
            })

            # 添加 AI 消息到历史
            history.append(response)

            # 检查是否有工具调用
            if response.tool_calls:
                # 执行工具调用
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call.get("id", f"call_{iteration}")

                    # 详细记录工具调用信息
                    logger.info({
                        "event": "agent_tool_call",
                        "conversation_id": conversation_id,
                        "iteration": iteration + 1,
                        "tool_name": tool_name,
                        "tool_id": tool_id,
                        "args_type": type(tool_args).__name__,
                        "args": tool_args
                    })

                    # 执行工具
                    try:
                        tool_result = await execute_tool(tool_name, tool_args, conversation_id)
                        tool_calls_executed.append({
                            "id": tool_id,
                            "name": tool_name,
                            "args": tool_args,
                            "result": str(tool_result)[:1000],
                        })

                        # 添加工具结果到历史
                        history.append(ToolMessage(
                            content=str(tool_result),
                            tool_call_id=tool_id,
                            name=tool_name
                        ))
                    except Exception as e:
                        error_msg = f"工具执行失败: {str(e)}"
                        history.append(ToolMessage(
                            content=error_msg,
                            tool_call_id=tool_id,
                            name=tool_name
                        ))

                continue  # 继续下一轮

            # 没有工具调用，任务完成
            final_response = response.content
            finish_reason = "stop"
            logger.debug({
                "event": "agent_chat_complete",
                "conversation_id": conversation_id,
                "finish_reason": "stop",
                "iterations_used": iteration + 1
            })
            break

        if finish_reason == "max_iterations":
            logger.warning({
                "event": "agent_max_iterations_reached",
                "conversation_id": conversation_id,
                "max_iterations": self.max_iterations
            })

        # 构建返回结果
        result = {
            "answer": final_response,
            "conversation_id": conversation_id,
            "tool_calls": tool_calls_executed,
            "finish_reason": finish_reason
        }

        # 添加 reasoning_content（如果存在）
        if hasattr(response, 'reasoning_content') and response.reasoning_content:
            result['reasoning_content'] = response.reasoning_content

        return result

    async def chat_stream(
        self,
        query: str,
        conversation_id: str,
        user_id: str = "default",
        inputs: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """流式对话 - 实时返回响应

        返回 SSE 格式的流数据

        Args:
            query: 用户输入
            conversation_id: 对话ID
            user_id: 用户ID
            inputs: 额外输入参数

        Yields:
            SSE 格式的数据行
        """
        # 获取或创建对话历史
        history = self.conversation_manager.get_or_create(conversation_id)

        # 如果是新对话，添加系统提示词
        if not history:
            system_prompt = get_system_prompt()
            history.append(SystemMessage(content=system_prompt))

        # 添加用户消息（严格遵循 1.json 格式 - content 为数组）
        user_content_parts = self._format_user_message(query, inputs)
        history.append(HumanMessage(content=user_content_parts))

        # 绑定工具
        llm_with_tools = self.llm.bind_tools(self.langchain_tools)

        # 发送开始事件
        yield f"data: {json.dumps({'type': 'start', 'conversation_id': conversation_id}, ensure_ascii=False)}\n\n"

        for iteration in range(self.max_iterations):
            # 流式调用
            full_content = ""
            reasoning_content = ""
            tool_calls_buffer = []

            async for chunk in llm_with_tools.astream(history):
                # 处理内容
                if chunk.content:
                    full_content += chunk.content
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk.content}, ensure_ascii=False)}\n\n"

                # 处理 reasoning_content（如果存在）
                if hasattr(chunk, 'reasoning_content') and chunk.reasoning_content:
                    reasoning_content += chunk.reasoning_content
                    yield f"data: {json.dumps({'type': 'reasoning', 'content': chunk.reasoning_content}, ensure_ascii=False)}\n\n"

                # 处理工具调用 - LangChain 流式工具调用处理
                if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                    for tc in chunk.tool_calls:
                        tool_calls_buffer.append(tc)

            # 构建完整消息
            if tool_calls_buffer:
                ai_msg = AIMessage(content=full_content, tool_calls=tool_calls_buffer)
            else:
                ai_msg = AIMessage(content=full_content)

            history.append(ai_msg)

            # 如果有工具调用，执行它们
            if tool_calls_buffer:
                yield f"data: {json.dumps({'type': 'tool_start', 'count': len(tool_calls_buffer)}, ensure_ascii=False)}\n\n"

                for tc in tool_calls_buffer:
                    tool_name = tc.get("name", "")
                    tool_args = tc.get("args", {})
                    tool_id = tc.get("id", f"call_{iteration}")

                    # 发送工具调用事件
                    yield f"data: {json.dumps({'type': 'tool_use', 'name': tool_name, 'arguments': tool_args}, ensure_ascii=False)}\n\n"

                    try:
                        result = await execute_tool(tool_name, tool_args, conversation_id)
                        yield f"data: {json.dumps({'type': 'tool_result', 'name': tool_name, 'status': 'success'}, ensure_ascii=False)}\n\n"

                        history.append(ToolMessage(
                            content=str(result),
                            tool_call_id=tool_id,
                            name=tool_name
                        ))

                        # 如果是 Skill 工具，注入 Skill 提示词
                        if tool_name == "Skill":
                            try:
                                result_data = json.loads(result)
                                if result_data.get("type") == "skill_activated":
                                    self._inject_skill_prompt(conversation_id, history)
                            except json.JSONDecodeError:
                                pass
                    except Exception as e:
                        error_msg = f"工具执行失败: {str(e)}"
                        yield f"data: {json.dumps({'type': 'tool_result', 'name': tool_name, 'status': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"

                        history.append(ToolMessage(
                            content=error_msg,
                            tool_call_id=tool_id,
                            name=tool_name
                        ))

                continue  # 继续下一轮

            # 任务完成
            done_event = {'type': 'done', 'finish_reason': 'stop'}
            if reasoning_content:
                done_event['reasoning_content'] = reasoning_content
            yield f"data: {json.dumps(done_event, ensure_ascii=False)}\n\n"
            break


# ==================== 全局 Agent 实例 ====================

_agent_instance: Optional[TraeAgent] = None


def get_agent() -> TraeAgent:
    """获取全局 Agent 实例 - 从 config.toml 加载配置"""
    global _agent_instance
    if _agent_instance is None:
        # 从当前文件位置计算项目根目录
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent.parent
        config_path = os.path.join(project_root, "config.toml")
        agent_config = {}

        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = toml.load(f)
                if "agent" in config:
                    agent_config = config["agent"]
            except Exception as e:
                logger.warning({
                    "event": "agent_config_load_failed",
                    "config_path": config_path,
                    "error": str(e)
                })

        # 从配置读取，如果没有则使用默认值
        model = agent_config.get("model", "qwen3.6-plus-2026-04-02")
        api_key = agent_config.get("api_key", "")
        base_url = agent_config.get("base_url", "https://api.openai.com/v1")
        max_iterations = agent_config.get("max_iterations", 10)

        _agent_instance = TraeAgent(
            model=model,
            api_key=api_key,
            base_url=base_url,
            max_iterations=max_iterations,
        )
    return _agent_instance
