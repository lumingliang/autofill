"""
AgentFactory - Agent 工厂

每个 session_id 对应唯一的 AgentRuntime 实例。
agent_name 与 tenant_id 仅作为该 runtime 的关联信息，用于按维度查询。
同一 Agent 的提示词、工具、Skill 等配置通过 AgentFactory 在全局共享。
"""
import functools
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from app.core.ctx import Ctx
from app.log import logger
from app.services.agent.agent_registry import AgentRegistry, get_agent_registry
from app.services.agent.agent_runtime import AgentRuntime
from app.services.agent.prompt_renderer import PromptRenderer, get_prompt_renderer
from app.services.agent.tool_registry import ToolRegistry, get_tool_registry


class AgentFactory:
    """Agent 工厂 - 持有全局共享的 Agent 配置、工具与 PromptRenderer"""

    def __init__(
        self,
        registry: AgentRegistry,
        tool_registry: ToolRegistry,
        prompt_renderer: PromptRenderer,
    ):
        self.registry = registry
        self.tool_registry = tool_registry
        self.prompt_renderer = prompt_renderer

    def create(self, agent_name: str) -> AgentRuntime:
        """根据 agent_name 创建新的 AgentRuntime 实例（共享全局配置）"""
        config = self.registry.get(agent_name)
        return AgentRuntime(
            config=config,
            tool_registry=self.tool_registry,
            prompt_renderer=self.prompt_renderer,
        )


# 全局 Agent 实例索引: session_id -> AgentRuntime
_agent_instances: Dict[str, AgentRuntime] = {}

# tenant_id/agent_name -> session_id 集合，用于按维度查询
_agent_sessions_by_tenant: Dict[str, Set[str]] = defaultdict(set)
_agent_sessions_by_agent: Dict[str, Set[str]] = defaultdict(set)


@functools.cache
def get_agent_factory() -> AgentFactory:
    """获取全局默认 Agent 工厂（懒加载、共享配置）"""
    return AgentFactory(
        registry=get_agent_registry(),
        tool_registry=get_tool_registry(),
        prompt_renderer=get_prompt_renderer(),
    )


def get_agent_runtime(
    agent_name: str = "default",
    tenant_id: str = "default",
    session_id: str = "default",
) -> AgentRuntime:
    """获取指定 session_id 的 AgentRuntime 实例（按 session_id 唯一）"""
    runtime = _agent_instances.get(session_id)
    if runtime is None:
        runtime = get_agent_factory().create(agent_name)
        _agent_instances[session_id] = runtime
        _agent_sessions_by_tenant[tenant_id].add(session_id)
        _agent_sessions_by_agent[agent_name].add(session_id)
        logger.info({
            "event": "agent_runtime_created",
            "tenant_id": tenant_id,
            "agent_name": agent_name,
            "session_id": session_id,
        })
    return runtime


def get_agent_runtimes_by_tenant(tenant_id: str) -> List[AgentRuntime]:
    """获取指定 tenant_id 下的所有 AgentRuntime"""
    return [
        _agent_instances[session_id]
        for session_id in _agent_sessions_by_tenant.get(tenant_id, set())
        if session_id in _agent_instances
    ]


def get_agent_runtimes_by_agent(agent_name: str) -> List[AgentRuntime]:
    """获取指定 agent_name 下的所有 AgentRuntime（跨租户）"""
    return [
        _agent_instances[session_id]
        for session_id in _agent_sessions_by_agent.get(agent_name, set())
        if session_id in _agent_instances
    ]


def get_agent_runtime_by_session(session_id: str) -> Optional[AgentRuntime]:
    """通过 session_id 直接查找 AgentRuntime"""
    return _agent_instances.get(session_id)


async def chat(
    agent_name: str,
    query: str,
    session_id: str,
    user_id: str = "default",
    inputs: Optional[Dict[str, Any]] = None,
    max_iterations: Optional[int] = None,
) -> Dict[str, Any]:
    """按名称调用 Agent（非流式）"""
    tenant_id = str(Ctx.get_effective_tenant_id())
    runtime = get_agent_runtime(agent_name, tenant_id, session_id)
    return await runtime.chat(
        query=query,
        session_id=session_id,
        user_id=user_id,
        inputs=inputs,
        max_iterations=max_iterations,
    )


async def chat_stream(
    agent_name: str,
    query: str,
    session_id: str,
    user_id: str = "default",
    inputs: Optional[Dict[str, Any]] = None,
    max_iterations: Optional[int] = None,
):
    """按名称调用 Agent（流式）"""
    tenant_id = str(Ctx.get_effective_tenant_id())
    runtime = get_agent_runtime(agent_name, tenant_id, session_id)
    async for event in runtime.chat_stream(
        query=query,
        session_id=session_id,
        user_id=user_id,
        inputs=inputs,
        max_iterations=max_iterations,
    ):
        yield event
