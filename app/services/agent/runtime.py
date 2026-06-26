"""
AgentRuntime - Agent 运行时

持有 Agent 规格、私有工具视图和编译后的 LangGraph，对外暴露 run/chat 接口。
"""
import asyncio
import uuid
from typing import Any, AsyncGenerator, Dict, Optional

from app.log import logger
from app.services.agent.graph.graph_builder import build_agent_graph
from app.services.agent.models import AgentSpec
from app.services.agent.prompt_renderer import get_prompt_renderer
from app.services.agent.state import AgentState, create_initial_state
from app.services.agent.tool_registry import get_tool_registry
from app.services.agent.trace import get_trace_logger


class AgentRuntime:
    """Agent 运行时"""

    def __init__(self, spec: AgentSpec, sub_agent_depth: int = 0):
        self.spec = spec
        self.sub_agent_depth = sub_agent_depth
        self.tools = get_tool_registry().build_agent_tools(spec)
        self.prompt_renderer = get_prompt_renderer()
        self.trace_logger = get_trace_logger()
        self.graph = build_agent_graph()

        logger.info({
            "event": "agent_runtime_initialized",
            "agent_name": spec.name,
            "model": spec.model,
            "tool_count": len(self.tools),
            "sub_agent_depth": sub_agent_depth,
        })

    def terminate(self) -> None:
        """终止当前运行时，取消所有运行中的子 Agent 任务"""
        # 运行时本身不持久持有子 Agent 任务句柄；清理由 Graph 状态中的 sub_agent_tree 决定。
        # 这里仅作为生命周期钩子，供上层 Factory 在 clear 时调用。
        logger.info({
            "event": "agent_runtime_terminated",
            "agent_name": self.spec.name,
        })

    async def run(
        self,
        session_id: str,
        query: str,
        user_id: str = "default",
        tenant_id: str = "default",
        inputs: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        parent_trace_id: Optional[str] = None,
        max_iterations: Optional[int] = None,
    ) -> Dict[str, Any]:
        """非流式执行一次 Agent 对话"""
        trace_id = trace_id or f"trace_{uuid.uuid4().hex}"
        max_iterations = max_iterations if max_iterations is not None else self.spec.max_iterations

        initial_state = create_initial_state(
            session_id=session_id,
            agent_id=self.spec.name,
            user_id=user_id,
            tenant_id=tenant_id,
            user_input=query,
            inputs=inputs,
            trace_id=trace_id,
            max_iterations=max_iterations,
            sub_agent_depth=self.sub_agent_depth,
            parent_trace_id=parent_trace_id,
        )

        config = {
            "recursion_limit": max(200, max_iterations * 6),
            "configurable": {"thread_id": session_id},
            "metadata": {
                "agent_spec": self.spec,
                "tools": self.tools,
                "prompt_renderer": self.prompt_renderer,
                "trace_logger": self.trace_logger,
                "tool_context": {
                    "session_id": session_id,
                    "agent_name": self.spec.name,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "agent_config": self.spec,
                },
            },
        }

        try:
            final_state = await self.graph.ainvoke(initial_state, config)
        except Exception as exc:
            logger.error({
                "event": "agent_run_error",
                "agent_name": self.spec.name,
                "session_id": session_id,
                "error": str(exc),
            })
            return {
                "answer": "",
                "session_id": session_id,
                "agent_name": self.spec.name,
                "finish_reason": "error",
                "error": str(exc),
                "trace_id": trace_id,
                "tool_calls": [],
            }

        final_state = final_state or {}
        return {
            "answer": final_state.get("final_answer", ""),
            "session_id": session_id,
            "agent_name": self.spec.name,
            "finish_reason": final_state.get("finish_reason", "stop"),
            "trace_id": trace_id,
            "tool_calls": final_state.get("final_tool_calls", []),
            "loop_detected": final_state.get("loop_detected", False),
            "loop_reason": final_state.get("loop_reason"),
        }

    async def chat_stream(
        self,
        session_id: str,
        query: str,
        user_id: str = "default",
        tenant_id: str = "default",
        inputs: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        parent_trace_id: Optional[str] = None,
        max_iterations: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """流式执行：通过 SSE 事件返回 content / tool_use / tool_result / done"""
        import json

        trace_id = trace_id or f"trace_{uuid.uuid4().hex}"
        max_iterations = max_iterations if max_iterations is not None else self.spec.max_iterations

        initial_state = create_initial_state(
            session_id=session_id,
            agent_id=self.spec.name,
            user_id=user_id,
            tenant_id=tenant_id,
            user_input=query,
            inputs=inputs,
            trace_id=trace_id,
            max_iterations=max_iterations,
            sub_agent_depth=self.sub_agent_depth,
            parent_trace_id=parent_trace_id,
        )

        queue: asyncio.Queue = asyncio.Queue()
        config = {
            "recursion_limit": max(200, max_iterations * 6),
            "configurable": {"thread_id": session_id},
            "metadata": {
                "agent_spec": self.spec,
                "tools": self.tools,
                "prompt_renderer": self.prompt_renderer,
                "trace_logger": self.trace_logger,
                "event_queue": queue,
                "tool_context": {
                    "session_id": session_id,
                    "agent_name": self.spec.name,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "agent_config": self.spec,
                },
            },
        }

        yield f"data: {json.dumps({'type': 'start', 'session_id': session_id, 'agent_name': self.spec.name, 'trace_id': trace_id}, ensure_ascii=False)}\n\n"

        run_task = asyncio.create_task(self.graph.ainvoke(initial_state, config))

        finish_reason = "stop"
        try:
            while True:
                # 如果图已经跑完，尽快消费完队列
                timeout = 0.1 if run_task.done() else 300.0
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=timeout)
                except asyncio.TimeoutError:
                    if run_task.done():
                        break
                    finish_reason = "timeout"
                    yield f"data: {json.dumps({'type': 'error', 'error': 'stream timeout'}, ensure_ascii=False)}\n\n"
                    break

                if event is None:
                    break

                if event.get("type") == "error":
                    finish_reason = "error"

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        finally:
            if not run_task.done():
                run_task.cancel()
                try:
                    await run_task
                except asyncio.CancelledError:
                    pass
            else:
                # 让异常暴露
                _ = run_task.exception()

        yield f"data: {json.dumps({'type': 'done', 'finish_reason': finish_reason, 'trace_id': trace_id}, ensure_ascii=False)}\n\n"
