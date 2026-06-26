"""
全链路 Trace 日志
"""
import functools
import time
from typing import Any, Dict, List, Optional

from app.log import logger
from app.services.agent.models import TraceEvent


class TraceLogger:
    """Trace 日志记录器"""

    def __init__(self):
        self._traces: Dict[str, List[TraceEvent]] = {}

    def emit(self, event: TraceEvent) -> None:
        """记录一个 Trace 事件"""
        self._traces.setdefault(event.trace_id, []).append(event)
        logger.info({"event": "agent_trace", "trace": event.model_dump(mode="json")})

    def log_step(
        self,
        trace_id: str,
        parent_trace_id: Optional[str],
        step_index: int,
        agent_id: str,
        session_id: str,
        node_name: str,
        event_type: str,
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[Dict[str, Any]] = None,
        state_delta: Optional[Dict[str, Any]] = None,
        latency_ms: int = 0,
    ) -> None:
        self.emit(
            TraceEvent(
                trace_id=trace_id,
                parent_trace_id=parent_trace_id,
                step_index=step_index,
                agent_id=agent_id,
                session_id=session_id,
                node_name=node_name,
                event_type=event_type,
                inputs=inputs,
                outputs=outputs,
                state_delta=state_delta,
                latency_ms=latency_ms,
            )
        )

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        steps = self._traces.get(trace_id, [])
        if not steps:
            return None
        return {
            "trace_id": trace_id,
            "step_count": len(steps),
            "agent_id": steps[0].agent_id,
            "session_id": steps[0].session_id,
            "start_time": steps[0].timestamp.isoformat(),
            "end_time": steps[-1].timestamp.isoformat(),
        }

    def get_steps(self, trace_id: str) -> List[Dict[str, Any]]:
        return [step.model_dump(mode="json") for step in self._traces.get(trace_id, [])]

    def get_step(self, trace_id: str, step_index: int) -> Optional[Dict[str, Any]]:
        steps = self._traces.get(trace_id, [])
        for step in steps:
            if step.step_index == step_index:
                return step.model_dump(mode="json")
        return None


@functools.cache
def get_trace_logger() -> TraceLogger:
    """获取全局 TraceLogger"""
    return TraceLogger()


def timed_step(node_name: str):
    """装饰器：记录节点执行耗时（支持同步/异步节点）"""
    def decorator(func):
        import inspect
        if inspect.iscoroutinefunction(func):
            async def async_wrapper(state, config):
                start = time.perf_counter()
                try:
                    result = await func(state, config)
                finally:
                    _log_step(state, config, node_name, start)
                return result
            return async_wrapper
        else:
            def sync_wrapper(state, config):
                start = time.perf_counter()
                try:
                    result = func(state, config)
                finally:
                    _log_step(state, config, node_name, start)
                return result
            return sync_wrapper
    return decorator


def _log_step(state, config, node_name, start):
    latency_ms = int((time.perf_counter() - start) * 1000)
    metadata = config.get("metadata", {})
    trace_logger = metadata.get("trace_logger")
    if trace_logger:
        trace_logger.log_step(
            trace_id=state.get("trace_id", ""),
            parent_trace_id=state.get("parent_trace_id"),
            step_index=state.get("iteration", 0),
            agent_id=state.get("agent_id", ""),
            session_id=state.get("session_id", ""),
            node_name=node_name,
            event_type="node_execute",
            latency_ms=latency_ms,
        )
