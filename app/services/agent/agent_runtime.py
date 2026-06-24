"""
AgentRuntime - Agent 运行时

持有本 Agent 的配置、LangChain 工具、LLM 和会话历史，对外暴露 chat 接口。
"""
from typing import Any, AsyncGenerator, Dict, List, Optional

from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from app.log import logger
from app.services.agent.agent_config import AgentConfig
from app.services.agent.agent_loop import AgentLoop
from app.services.agent.conversation_manager import ConversationManager
from app.services.agent.prompt_renderer import PromptRenderer, get_prompt_renderer
from app.services.agent.tool_registry import ToolRegistry, get_tool_registry


class AgentRuntime:
    """Agent 运行时"""

    def __init__(
        self,
        config: AgentConfig,
        tool_registry: ToolRegistry,
        prompt_renderer: PromptRenderer,
    ):
        self.config = config
        self.tool_registry = tool_registry
        self.prompt_renderer = prompt_renderer

        # 构建并缓存本 Agent 的 langchain_tools
        self.langchain_tools: List[BaseTool] = self._build_langchain_tools()

        # 创建 LLM
        self.llm = ChatOpenAI(
            model=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
            temperature=config.temperature,
            streaming=True,
        )

        # 维护本 Agent 的会话历史
        self.conversation_manager = ConversationManager(max_history=config.max_history)

        # Agent Loop
        self.loop = AgentLoop(
            config=config,
            tools=self.langchain_tools,
            llm=self.llm,
            conversation_manager=self.conversation_manager,
            prompt_renderer=self.prompt_renderer,
        )

        logger.info({
            "event": "agent_runtime_initialized",
            "agent_name": config.name,
            "model": config.model,
            "tools": [t.name for t in self.langchain_tools]
        })

    def _build_langchain_tools(self) -> List[BaseTool]:
        """构建本 Agent 的 LangChain 工具列表"""
        allowed_skills = self.config.skills if self.config.skills else None
        return self.tool_registry.get_many(self.config.tools, allowed_skills=allowed_skills)

    async def chat(
        self,
        query: str,
        session_id: str,
        user_id: str = "default",
        inputs: Optional[Dict[str, Any]] = None,
        max_iterations: Optional[int] = None,
        debug: bool = False,
    ) -> Dict[str, Any]:
        """非流式对话"""
        return await self.loop.run(
            session_id=session_id,
            query=query,
            user_id=user_id,
            inputs=inputs,
            max_iterations=max_iterations,
            debug=debug,
        )

    async def chat_stream(
        self,
        query: str,
        session_id: str,
        user_id: str = "default",
        inputs: Optional[Dict[str, Any]] = None,
        max_iterations: Optional[int] = None,
        debug: bool = False,
    ) -> AsyncGenerator[str, None]:
        """流式对话"""
        async for event in self.loop.run_stream(
            session_id=session_id,
            query=query,
            user_id=user_id,
            inputs=inputs,
            max_iterations=max_iterations,
            debug=debug,
        ):
            yield event
