"""
Agent StateGraph 构建器
"""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.services.agent.graph.edges import (
    route_after_llm,
    route_after_loop_detect,
    route_after_termination,
    route_after_tool_dispatch,
)
from app.services.agent.graph.nodes import (
    loop_detect_node,
    output_node,
    prepare_node,
    sub_agent_dispatch_node,
    sub_agent_wait_node,
    termination_check_node,
    tool_dispatch_node,
    tool_execute_node,
    llm_call_node,
)
from app.services.agent.state import AgentState


def build_agent_graph():
    """构建并返回编译后的 Agent 状态图"""
    workflow = StateGraph(AgentState)

    workflow.add_node("prepare", prepare_node)
    workflow.add_node("llm_call", llm_call_node)
    workflow.add_node("tool_dispatch", tool_dispatch_node)
    workflow.add_node("tool_execute", tool_execute_node)
    workflow.add_node("sub_agent_dispatch", sub_agent_dispatch_node)
    workflow.add_node("sub_agent_wait", sub_agent_wait_node)
    workflow.add_node("loop_detect", loop_detect_node)
    workflow.add_node("termination_check", termination_check_node)
    workflow.add_node("output", output_node)

    workflow.add_edge(START, "prepare")
    workflow.add_edge("prepare", "llm_call")
    workflow.add_conditional_edges("llm_call", route_after_llm)
    workflow.add_conditional_edges("tool_dispatch", route_after_tool_dispatch)
    workflow.add_edge("tool_execute", "loop_detect")
    workflow.add_edge("sub_agent_dispatch", "sub_agent_wait")
    workflow.add_edge("sub_agent_wait", "loop_detect")
    workflow.add_conditional_edges("loop_detect", route_after_loop_detect)
    workflow.add_conditional_edges("termination_check", route_after_termination)
    workflow.add_edge("output", END)

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)
