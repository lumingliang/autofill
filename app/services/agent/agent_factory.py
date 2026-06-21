"""
AgentFactory - Agent 工厂

根据 agent_name 创建或复用 AgentRuntime 实例。
"""
from typing import Any, Dict, Optional

from app.log import logger
from app.services.agent.agent_registry import AgentRegistry, get_agent_registry
from app.services.agent.agent_runtime import AgentRuntime
from app.services.agent.prompt_renderer import PromptRenderer, get_prompt_renderer
from app.services.agent.tool_registry import ToolRegistry, get_tool_registry


class AgentFactory:
    """Agent 工厂"""

    def __init__(
        self,
        registry: AgentRegistry,
        tool_registry: ToolRegistry,
        prompt_renderer: PromptRenderer,
    ):
        self.registry = registry
        self.tool_registry = tool_registry
        self.prompt_renderer = prompt_renderer
        self._runtimes: Dict[str, AgentRuntime] = {}

    def create(self, agent_name: str) -> AgentRuntime:
        """根据 agent_name 创建新的 AgentRuntime 实例"""
        config = self.registry.get(agent_name)
        return AgentRuntime(
            config=config,
            tool_registry=self.tool_registry,
            prompt_renderer=self.prompt_renderer,
        )

    def get_or_create(self, agent_name: str) -> AgentRuntime:
        """根据 agent_name 获取或创建 AgentRuntime 实例（缓存）"""
        if agent_name not in self._runtimes:
            self._runtimes[agent_name] = self.create(agent_name)
            logger.info({"event": "agent_runtime_created", "agent_name": agent_name})
        return self._runtimes[agent_name]

    def clear_cache(self) -> None:
        """清空运行时缓存"""
        self._runtimes.clear()


# 全局默认 Agent 工厂实例
_default_agent_factory: Optional[AgentFactory] = None


def get_agent_factory() -> AgentFactory:
    """获取全局默认 Agent 工厂（懒加载）"""
    global _default_agent_factory
    if _default_agent_factory is None:
        _default_agent_factory = AgentFactory(
            registry=get_agent_registry(),
            tool_registry=get_tool_registry(),
            prompt_renderer=get_prompt_renderer(),
        )
    return _default_agent_factory


def get_agent_runtime(agent_name: str = "default") -> AgentRuntime:
    """获取指定 Agent 的运行时实例"""
    return get_agent_factory().get_or_create(agent_name)


async def chat(
    agent_name: str,
    query: str,
    session_id: str,
    tenant_id: str,
    user_id: str = "default",
    inputs: Optional[Dict[str, Any]] = None,
    max_iterations: Optional[int] = None,
) -> Dict[str, Any]:
    """按名称调用 Agent（非流式）"""
    factory = get_agent_factory()
    runtime = factory.get_or_create(agent_name)
    return await runtime.chat(
        query=query,
        session_id=session_id,
        tenant_id=tenant_id,
        user_id=user_id,
        inputs=inputs,
        max_iterations=max_iterations,
    )


async def chat_stream(
    agent_name: str,
    query: str,
    session_id: str,
    tenant_id: str,
    user_id: str = "default",
    inputs: Optional[Dict[str, Any]] = None,
    max_iterations: Optional[int] = None,
):
    """按名称调用 Agent（流式）"""
    factory = get_agent_factory()
    runtime = factory.get_or_create(agent_name)
    async for event in runtime.chat_stream(
        query=query,
        session_id=session_id,
        tenant_id=tenant_id,
        user_id=user_id,
        inputs=inputs,
        max_iterations=max_iterations,
    ):
        yield event
