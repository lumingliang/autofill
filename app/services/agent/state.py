"""
Agent LangGraph State 定义

使用 MessagesState 作为基类，保证 messages 字段使用 add_messages reducer。
"""
from typing import Any, Dict, List, Literal, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import MessagesState


class SubAgentRequest(TypedDict, total=False):
    """子 Agent 调用请求记录"""

    call_id: str
    agent_name: str
    query: str
    inputs: Optional[Dict[str, Any]]
    status: Literal["pending", "running", "done", "error", "loop_detected"]
    result: Optional[Dict[str, Any]]
    trace_id: str
    session_id: str


class SubAgentRuntimeSnapshot(TypedDict, total=False):
    """子 Agent 运行时快照，保存在父 Agent State 中"""

    agent_name: str
    agent_id: str
    session_id: str
    trace_id: str
    parent_session_id: str
    depth: int
    status: Literal["pending", "running", "done", "error", "loop_detected"]
    task: Optional[Any]
    created_at: str
    finished_at: Optional[str]
    finish_reason: Optional[str]
    final_state_summary: Optional[Dict[str, Any]]


class AgentState(MessagesState):
    """Agent 状态

    继承 MessagesState，messages 字段自带 add_messages reducer。
    """

    # 身份与元数据
    trace_id: str
    parent_trace_id: Optional[str]
    session_id: str
    agent_id: str
    tenant_id: str
    user_id: str

    # 输入
    user_input: str
    inputs: Optional[Dict[str, Any]]

    # 工具视图（OpenAI 格式描述快照，仅用于日志/调试）
    tool_view: Optional[List[Dict[str, Any]]]
    # 最近一条 AI 消息（用于终止判断）
    last_ai_message: Optional[BaseMessage]
    # 当前待执行的工具调用缓冲
    tool_calls_buffer: List[Dict[str, Any]]

    # 子 Agent
    sub_agent_requests: List[SubAgentRequest]
    sub_agent_tree: Dict[str, SubAgentRuntimeSnapshot]
    sub_agent_depth: int

    # 循环检测
    fingerprint_window: List[Dict[str, Any]]
    loop_detected: bool
    loop_reason: Optional[str]

    # 终止
    iteration: int
    max_iterations: int
    finish_reason: Optional[Literal["stop", "max_iterations", "loop_detected", "error"]]

    # 输出
    final_answer: str
    final_tool_calls: List[Dict[str, Any]]
    error_message: Optional[str]


def create_initial_state(
    session_id: str,
    agent_id: str,
    user_id: str,
    tenant_id: str,
    user_input: str,
    inputs: Optional[Dict[str, Any]],
    trace_id: str,
    max_iterations: int,
    sub_agent_depth: int = 0,
    parent_trace_id: Optional[str] = None,
) -> AgentState:
    """创建新的 AgentState"""
    return AgentState(
        trace_id=trace_id,
        parent_trace_id=parent_trace_id,
        session_id=session_id,
        agent_id=agent_id,
        tenant_id=tenant_id,
        user_id=user_id,
        user_input=user_input,
        inputs=inputs or {},
        messages=[],
        tool_view=None,
        last_ai_message=None,
        tool_calls_buffer=[],
        sub_agent_requests=[],
        sub_agent_tree={},
        sub_agent_depth=sub_agent_depth,
        fingerprint_window=[],
        loop_detected=False,
        loop_reason=None,
        iteration=0,
        max_iterations=max_iterations,
        finish_reason=None,
        final_answer="",
        final_tool_calls=[],
        error_message=None,
    )


def derive_child_session_id(parent_session_id: str, agent_name: str, call_index: int) -> str:
    """生成子 Agent 派生 session_id"""
    return f"{parent_session_id}/sub/{agent_name}/{call_index}"
