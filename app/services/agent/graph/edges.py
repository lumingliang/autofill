"""
Agent LangGraph 条件边
"""
from typing import Literal

from app.services.agent.state import AgentState


def route_after_llm(state: AgentState) -> Literal["tool_dispatch", "termination_check"]:
    """LLM 调用后：有 tool_calls 则进入工具分发，否则进入终止校验"""
    ai_msg = state.get("last_ai_message")
    if ai_msg and getattr(ai_msg, "tool_calls", None):
        return "tool_dispatch"
    return "termination_check"


def route_after_tool_dispatch(state: AgentState) -> Literal["sub_agent_dispatch", "tool_execute"]:
    """工具分发后：包含 run_agent 则进入子 Agent 调度，否则执行普通工具"""
    tool_calls = state.get("tool_calls_buffer", [])
    if any(tc.get("name") == "run_agent" for tc in tool_calls):
        return "sub_agent_dispatch"
    return "tool_execute"


def route_after_loop_detect(state: AgentState) -> Literal["output", "llm_call"]:
    """循环检测后：若触发熔断则输出，否则继续 LLM 调用"""
    if state.get("loop_detected"):
        return "output"
    return "llm_call"


def route_after_termination(
    state: AgentState,
) -> Literal["output", "sub_agent_wait", "llm_call"]:
    """终止校验后：决定下一步"""
    finish_reason = state.get("finish_reason")
    if finish_reason in ("stop", "max_iterations", "loop_detected", "error"):
        return "output"

    sub_agent_tree = state.get("sub_agent_tree", {})
    if any(s.get("status") in ("pending", "running") for s in sub_agent_tree.values()):
        return "sub_agent_wait"

    return "llm_call"
