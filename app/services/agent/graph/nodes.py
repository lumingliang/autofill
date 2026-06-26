"""
Agent LangGraph 节点实现
"""
import asyncio
import datetime
import hashlib
import json
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from app.log import logger
from app.services.agent.loop_detection import detect_loop
from app.services.agent.models import AgentSpec, Fingerprint, TerminationResult
from app.services.agent.prompt import build_system_prompt, build_user_message
from app.services.agent.state import AgentState, SubAgentRequest, SubAgentRuntimeSnapshot, derive_child_session_id
from app.services.agent.termination import TerminationChecker
from app.services.agent.tool_executor import format_tool_result
from app.services.agent.trace import timed_step

# 子 Agent 运行时任务句柄（不可被 checkpoint 序列化），按 child_session_id 临时存放
_sub_agent_tasks: Dict[str, asyncio.Task] = {}


@timed_step("prepare")
async def prepare_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """准备节点：注入 system prompt 和用户消息"""
    metadata = config.get("metadata", {})
    spec: AgentSpec = metadata["agent_spec"]
    prompt_renderer = metadata.get("prompt_renderer")

    user_msg = build_user_message(state["user_input"], state.get("inputs"), spec)

    # 新会话：需要注入 system prompt
    if not state.get("messages"):
        system_prompt = await build_system_prompt(spec, prompt_renderer)
        return {"messages": [SystemMessage(content=system_prompt), user_msg]}

    # 已存在会话：仅追加用户消息
    return {"messages": [user_msg]}


@timed_step("llm_call")
async def llm_call_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """LLM 调用节点"""
    metadata = config.get("metadata", {})
    spec: AgentSpec = metadata["agent_spec"]
    tools = metadata.get("tools", [])

    llm = ChatOpenAI(
        model=spec.model,
        api_key=spec.api_key,
        base_url=spec.base_url,
        temperature=spec.temperature,
        streaming=True,
    )
    llm_with_tools = llm.bind_tools(tools) if tools else llm

    messages = state.get("messages", [])
    queue = metadata.get("event_queue")

    response = await llm_with_tools.ainvoke(messages)
    ai_msg = response if isinstance(response, AIMessage) else AIMessage(content=str(response.content))

    # 流式模式下将最终回答内容切分后推入事件队列，保持工具调用的准确性
    if queue and ai_msg.content and not ai_msg.tool_calls:
        chunk_size = 6
        content = ai_msg.content
        for i in range(0, len(content), chunk_size):
            await queue.put({"type": "content", "content": content[i:i + chunk_size]})

    return {
        "messages": [ai_msg],
        "last_ai_message": ai_msg,
        "iteration": state.get("iteration", 0) + 1,
    }


@timed_step("tool_dispatch")
async def tool_dispatch_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """工具分发节点：解析最近一次 AI 消息中的 tool_calls"""
    ai_msg = state.get("last_ai_message")
    tool_calls = []
    if ai_msg and hasattr(ai_msg, "tool_calls") and ai_msg.tool_calls:
        tool_calls = list(ai_msg.tool_calls)

    queue = config.get("metadata", {}).get("event_queue")
    if queue and tool_calls:
        await queue.put({"type": "tool_start", "count": len(tool_calls)})
        for tc in tool_calls:
            await queue.put({
                "type": "tool_use",
                "name": tc.get("name", ""),
                "arguments": tc.get("args", {}),
            })

    existing = list(state.get("final_tool_calls", []))
    return {"tool_calls_buffer": tool_calls, "final_tool_calls": existing + tool_calls}


@timed_step("tool_execute")
async def tool_execute_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """普通工具执行节点（不包含 run_agent）"""
    metadata = config.get("metadata", {})
    tools = metadata.get("tools", [])
    tool_context = metadata.get("tool_context", {})

    tool_map = {tool.name: tool for tool in tools}
    tool_calls = state.get("tool_calls_buffer", [])

    tasks = []
    for tc in tool_calls:
        tool_name = tc.get("name")
        tool = tool_map.get(tool_name)
        if tool is None:
            tasks.append(
                asyncio.sleep(0, result=format_tool_result("error", {"error": f"Unknown tool: {tool_name}"}))
            )
            continue
        runnable_config = RunnableConfig(metadata={"tool_context": tool_context})
        tasks.append(tool.ainvoke(tc.get("args", {}), config=runnable_config))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    queue = metadata.get("event_queue")
    tool_messages = []
    for tc, result in zip(tool_calls, results):
        if isinstance(result, Exception):
            content = format_tool_result("error", {"error": str(result)})
            status = "error"
        else:
            content = str(result)
            status = "done"
        tool_messages.append(
            ToolMessage(
                content=content,
                tool_call_id=tc.get("id", "call_unknown"),
                name=tc.get("name", ""),
            )
        )
        if queue:
            await queue.put({
                "type": "tool_result",
                "name": tc.get("name", ""),
                "status": status,
                "result": content,
            })

    return {"messages": tool_messages, "tool_calls_buffer": []}


@timed_step("sub_agent_dispatch")
async def sub_agent_dispatch_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """子 Agent 调度节点：创建并启动子 Agent 任务"""
    metadata = config.get("metadata", {})
    spec: AgentSpec = metadata["agent_spec"]

    # 延迟导入避免循环依赖
    from app.services.agent.factory import AgentFactory
    from app.services.agent.registry import get_agent_registry
    from app.services.agent.runtime import AgentRuntime

    registry = get_agent_registry()
    tool_calls = state.get("tool_calls_buffer", [])

    requests: List[SubAgentRequest] = []
    tree = dict(state.get("sub_agent_tree", {}))
    depth = state.get("sub_agent_depth", 0)
    parent_session_id = state["session_id"]
    parent_trace_id = state["trace_id"]

    run_agent_calls = [tc for tc in tool_calls if tc.get("name") == "run_agent"]
    for idx, tc in enumerate(run_agent_calls):
        args = tc.get("args", {})
        agent_name = args.get("agent_name")
        query = args.get("query", "")
        inputs = args.get("inputs") or {}
        inherit_context = args.get("inherit_context", True)
        max_iterations = args.get("max_iterations")

        call_id = tc.get("id", f"call_{idx}")
        child_session_id = derive_child_session_id(parent_session_id, agent_name or "unknown", idx)
        child_trace_id = f"{parent_trace_id}/{agent_name or 'unknown'}/{idx}"

        if depth + 1 > spec.max_sub_agent_depth:
            error_msg = format_tool_result("error", {"error": f"Max sub-agent depth {spec.max_sub_agent_depth} exceeded"})
            requests.append(
                SubAgentRequest(
                    call_id=call_id,
                    agent_name=agent_name or "",
                    query=query,
                    inputs=inputs,
                    status="error",
                    result={"answer": "", "finish_reason": "error", "error": error_msg},
                    trace_id=child_trace_id,
                    session_id=child_session_id,
                )
            )
            tree[child_session_id] = SubAgentRuntimeSnapshot(
                agent_name=agent_name or "",
                agent_id=agent_name or "",
                session_id=child_session_id,
                trace_id=child_trace_id,
                parent_session_id=parent_session_id,
                depth=depth + 1,
                status="error",
                task=None,
                created_at=datetime.datetime.utcnow().isoformat(),
                finished_at=datetime.datetime.utcnow().isoformat(),
                finish_reason="error",
                final_state_summary={"error": error_msg},
            )
            continue

        if not registry.has(agent_name):
            error_msg = format_tool_result("error", {"error": f"Agent '{agent_name}' not found"})
            requests.append(
                SubAgentRequest(
                    call_id=call_id,
                    agent_name=agent_name or "",
                    query=query,
                    inputs=inputs,
                    status="error",
                    result={"answer": "", "finish_reason": "error", "error": error_msg},
                    trace_id=child_trace_id,
                    session_id=child_session_id,
                )
            )
            tree[child_session_id] = SubAgentRuntimeSnapshot(
                agent_name=agent_name or "",
                agent_id=agent_name or "",
                session_id=child_session_id,
                trace_id=child_trace_id,
                parent_session_id=parent_session_id,
                depth=depth + 1,
                status="error",
                task=None,
                created_at=datetime.datetime.utcnow().isoformat(),
                finished_at=datetime.datetime.utcnow().isoformat(),
                finish_reason="error",
                final_state_summary={"error": error_msg},
            )
            continue

        child_spec = registry.get(agent_name)
        child_inputs = dict(inputs)
        if inherit_context:
            child_inputs.setdefault("parent_trace_id", parent_trace_id)
            child_inputs.setdefault("parent_session_id", parent_session_id)

        child_runtime = AgentRuntime(
            spec=child_spec,
            sub_agent_depth=depth + 1,
        )

        task = asyncio.create_task(
            child_runtime.run(
                session_id=child_session_id,
                query=query,
                user_id=state.get("user_id", "default"),
                tenant_id=state.get("tenant_id", "default"),
                inputs=child_inputs,
                trace_id=child_trace_id,
                parent_trace_id=parent_trace_id,
                max_iterations=max_iterations,
            )
        )
        _sub_agent_tasks[child_session_id] = task

        requests.append(
            SubAgentRequest(
                call_id=call_id,
                agent_name=agent_name,
                query=query,
                inputs=inputs,
                status="running",
                result=None,
                trace_id=child_trace_id,
                session_id=child_session_id,
            )
        )
        tree[child_session_id] = SubAgentRuntimeSnapshot(
            agent_name=agent_name,
            agent_id=agent_name,
            session_id=child_session_id,
            trace_id=child_trace_id,
            parent_session_id=parent_session_id,
            depth=depth + 1,
            status="running",
            task=None,
            created_at=datetime.datetime.utcnow().isoformat(),
            finished_at=None,
            finish_reason=None,
            final_state_summary=None,
        )

    return {
        "sub_agent_requests": requests,
        "sub_agent_tree": tree,
        "tool_calls_buffer": [],
    }


@timed_step("sub_agent_wait")
async def sub_agent_wait_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """子 Agent 等待节点：等待所有运行中的子 Agent 并收集结果"""
    metadata = config.get("metadata", {})
    queue = metadata.get("event_queue")
    requests = list(state.get("sub_agent_requests", []))
    tree = dict(state.get("sub_agent_tree", {}))

    tool_messages = []
    updated_requests: List[SubAgentRequest] = []

    for req in requests:
        if req["status"] != "running":
            updated_requests.append(req)
            continue

        session_id = req["session_id"]
        task = _sub_agent_tasks.pop(session_id, None)

        if task is None:
            req["status"] = "error"
            updated_requests.append(req)
            continue

        try:
            result = await task
        except Exception as exc:
            result = {
                "answer": "",
                "finish_reason": "error",
                "error": str(exc),
            }
            req["status"] = "error"
        else:
            finish_reason = result.get("finish_reason", "stop")
            if finish_reason == "loop_detected":
                req["status"] = "loop_detected"
            elif finish_reason == "error":
                req["status"] = "error"
            else:
                req["status"] = "done"

        req["result"] = result
        updated_requests.append(req)

        if session_id in tree:
            tree[session_id]["status"] = req["status"]
            tree[session_id]["finished_at"] = datetime.datetime.utcnow().isoformat()
            tree[session_id]["finish_reason"] = result.get("finish_reason", "stop")
            tree[session_id]["final_state_summary"] = {
                "answer": result.get("answer", "")[:500],
                "finish_reason": result.get("finish_reason", "stop"),
                "tool_calls_count": len(result.get("tool_calls", [])),
            }
            tree[session_id]["task"] = None

        result_text = json.dumps(result, ensure_ascii=False, indent=2)
        tool_messages.append(
            ToolMessage(
                content=result_text,
                tool_call_id=req["call_id"],
                name=req["agent_name"],
            )
        )
        if queue:
            await queue.put({
                "type": "tool_result",
                "name": req["agent_name"],
                "status": req["status"],
                "result": result,
            })

    return {
        "messages": tool_messages,
        "sub_agent_requests": updated_requests,
        "sub_agent_tree": tree,
    }


@timed_step("loop_detect")
async def loop_detect_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """循环检测节点"""
    metadata = config.get("metadata", {})
    spec: AgentSpec = metadata["agent_spec"]

    window = list(state.get("fingerprint_window", []))
    ai_msg = state.get("last_ai_message")
    if not ai_msg or not getattr(ai_msg, "tool_calls", None):
        return {"fingerprint_window": window}

    new_fingerprints = []
    for tc in ai_msg.tool_calls:
        args = tc.get("args", {})
        normalized = json.dumps(args, sort_keys=True, ensure_ascii=False)
        preview = normalized[: spec.loop_detection.max_fingerprint_args_len]
        fp = Fingerprint(
            agent_id=state.get("agent_id", ""),
            call_type="sub_agent" if tc.get("name") == "run_agent" else "tool",
            name=tc.get("name", ""),
            args_hash=hashlib.sha256(normalized.encode()).hexdigest()[:16],
            args_preview=preview,
            todo_count=0,
        )
        new_fingerprints.append(fp.model_dump())

    window.extend(new_fingerprints)
    window = window[-spec.loop_detection.window_size :]

    loop_detected, loop_reason = detect_loop(window, spec.loop_detection)

    return {
        "fingerprint_window": window,
        "loop_detected": loop_detected,
        "loop_reason": loop_reason if loop_detected else None,
    }


@timed_step("termination_check")
def termination_check_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """终止校验节点"""
    metadata = config.get("metadata", {})
    spec: AgentSpec = metadata["agent_spec"]

    checker = TerminationChecker()
    result: TerminationResult = checker.check(state, spec)

    updates: Dict[str, Any] = {}
    if result.can_finish:
        updates["finish_reason"] = "stop"
    elif result.finish_reason:
        updates["finish_reason"] = result.finish_reason
    return updates


@timed_step("output")
def output_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """输出节点：组装最终响应"""
    messages = state.get("messages", [])
    final_answer = ""
    if messages:
        last_msg = messages[-1]
        if isinstance(last_msg, AIMessage):
            final_answer = last_msg.content or ""
        else:
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    final_answer = msg.content or ""
                    break

    finish_reason = state.get("finish_reason")
    if not finish_reason:
        finish_reason = "loop_detected" if state.get("loop_detected") else "stop"
    return {
        "final_answer": final_answer,
        "finish_reason": finish_reason,
        "final_tool_calls": state.get("final_tool_calls", []),
    }
