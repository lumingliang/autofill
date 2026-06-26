"""
AgentFactory - Agent 运行时工厂

按 session_id 管理主 Agent 运行时实例；子 Agent 运行时由父 Agent 直接创建，不进入全局缓存。
"""
import functools
from typing import Any, AsyncGenerator, Dict, Optional

from app.core.ctx import Ctx
from app.log import logger
from app.services.agent.models import AgentSpec
from app.services.agent.registry import AgentRegistry, get_agent_registry
from app.services.agent.runtime import AgentRuntime


class AgentFactory:
    """Agent 工厂"""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        # 仅缓存主 Agent 运行时（按 session_id）
        self._main_runtimes: Dict[str, AgentRuntime] = {}

    def get_or_create(self, agent_name: str, session_id: str) -> AgentRuntime:
        """获取或创建主 Agent 运行时"""
        runtime = self._main_runtimes.get(session_id)
        if runtime is None or runtime.spec.name != agent_name:
            spec = self.registry.get(agent_name)
            runtime = AgentRuntime(spec)
            self._main_runtimes[session_id] = runtime
            logger.info({
                "event": "agent_runtime_created",
                "agent_name": agent_name,
                "session_id": session_id,
            })
        return runtime

    def get_by_session(self, session_id: str) -> Optional[AgentRuntime]:
        return self._main_runtimes.get(session_id)

    def remove_by_session(self, session_id: str) -> bool:
        if session_id in self._main_runtimes:
            del self._main_runtimes[session_id]
            return True
        return False

    def create_child(self, spec: AgentSpec, parent_state: Dict, call_index: int) -> AgentRuntime:
        """创建子 Agent 运行时（不缓存）"""
        return AgentRuntime(spec, sub_agent_depth=parent_state.get("sub_agent_depth", 0) + 1)


@functools.cache
def get_agent_factory() -> AgentFactory:
    return AgentFactory(registry=get_agent_registry())


async def chat(
    agent_name: str,
    query: str,
    session_id: str,
    user_id: str = "default",
    inputs: Optional[Dict] = None,
    max_iterations: Optional[int] = None,
) -> Dict[str, Any]:
    """按名称调用主 Agent（非流式）"""
    tenant_id = str(Ctx.get_effective_tenant_id())
    factory = get_agent_factory()
    runtime = factory.get_or_create(agent_name, session_id)
    return await runtime.run(
        session_id=session_id,
        query=query,
        user_id=user_id,
        tenant_id=tenant_id,
        inputs=inputs,
        max_iterations=max_iterations,
    )


async def chat_stream(
    agent_name: str,
    query: str,
    session_id: str,
    user_id: str = "default",
    inputs: Optional[Dict] = None,
    max_iterations: Optional[int] = None,
) -> AsyncGenerator[str, None]:
    tenant_id = str(Ctx.get_effective_tenant_id())
    factory = get_agent_factory()
    runtime = factory.get_or_create(agent_name, session_id)
    async for event in runtime.chat_stream(
        session_id=session_id,
        query=query,
        user_id=user_id,
        tenant_id=tenant_id,
        inputs=inputs,
        max_iterations=max_iterations,
    ):
        yield event
