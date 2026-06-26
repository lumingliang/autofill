"""
多层终止校验器
"""
from typing import Optional

from app.services.agent.models import AgentSpec, TerminationResult
from app.services.agent.state import AgentState
from app.services.agent.todo_manager import todo_manager


class TerminationChecker:
    """多层终止校验"""

    def check(self, state: AgentState, spec: AgentSpec) -> TerminationResult:
        # 1. 循环检测层
        if state.get("loop_detected"):
            return TerminationResult(can_finish=False, failed_layer="loop", reason=state.get("loop_reason"))

        # 2. 最大迭代次数层
        if state.get("iteration", 0) >= spec.max_iterations:
            return TerminationResult(can_finish=False, failed_layer="max_iterations", reason="Max iterations reached", finish_reason="max_iterations")

        ai_msg = state.get("last_ai_message")

        # 3. 工具调用层
        if ai_msg and getattr(ai_msg, "tool_calls", None):
            return TerminationResult(can_finish=False, failed_layer="tool_calls_pending", reason="Tool calls pending")

        # 4. LLM finish_reason 层
        if spec.termination_policy.check_finish_reason_stop:
            finish_reason = getattr(ai_msg, "response_metadata", {}).get("finish_reason") if ai_msg else None
            if finish_reason != "stop":
                return TerminationResult(can_finish=False, failed_layer="finish_reason", reason="LLM finish_reason is not stop")

        # 5. TODO 层
        if spec.termination_policy.check_todos:
            todos = todo_manager.get_todos(state["session_id"])
            if todos and any(t.get("status") in ("pending", "in_progress") for t in todos):
                return TerminationResult(can_finish=False, failed_layer="todos", reason="Pending or in-progress todos exist")

        # 6. 子 Agent 层
        if spec.termination_policy.check_sub_agents:
            tree = state.get("sub_agent_tree", {})
            if any(s.get("status") in ("pending", "running") for s in tree.values()):
                return TerminationResult(can_finish=False, failed_layer="sub_agents", reason="Sub-agents still running")

        return TerminationResult(can_finish=True)
