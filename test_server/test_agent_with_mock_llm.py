"""
End-to-end test of the refactored Agent against a mock LLM server.

Usage:
    1. Start the mock LLM server:
       python test_server/mock_llm_server.py

    2. In another terminal run:
       python test_server/test_agent_with_mock_llm.py

The script will:
    - Create a temporary AgentRuntime whose LLM points to the mock server.
    - Send a user query.
    - Print every request sent to the LLM and every tool call executed.
    - Assert that the interaction matches expectations.
"""
import asyncio
import json
import sys
from typing import Any, Dict, List

sys.path.insert(0, "/Users/lu/code/code/py/autofill")

from app.services.agent.agent_config import AgentConfig
from app.services.agent.agent_runtime import AgentRuntime
from app.services.agent.prompt_renderer import get_prompt_renderer
from app.services.agent.tool_registry import ToolRegistry, get_tool_registry


async def run_test(stream: bool = False, session_suffix: str = "") -> Dict[str, Any]:
    print("=" * 70)
    print(f"Agent E2E Test (stream={stream})")
    print("=" * 70)

    # Build an agent config that talks to the mock LLM server
    config = AgentConfig(
        name="test_default",
        display_name="Test Agent",
        description="Test agent for mock LLM interaction",
        model="mock-model",
        api_key="mock-api-key",
        base_url="http://127.0.0.1:9998/v1",
        temperature=0.0,
        max_tokens=1024,
        tools=[
            "Skill",
            "Glob",
            "LS",
            "Grep",
            "Read",
            "RunCommand",
            "TodoWrite",
            "SearchReplace",
            "Write",
            "DeleteFile",
            "AskUserQuestion",
        ],
        skills=[],
        system_prompt_sections=["introduction", "system", "doing_tasks"],
        max_iterations=3,
        max_history=10,
    )

    registry = get_tool_registry()
    prompt_renderer = get_prompt_renderer()
    runtime = AgentRuntime(config, registry, prompt_renderer)

    session_id = f"test-session-001{session_suffix}"
    tenant_id = "test-tenant"
    query = "请帮我查看 agent_loop.py 的前几行内容"

    print(f"\n[TEST] Query: {query}")
    print(f"[TEST] Session: {session_id} Tenant: {tenant_id}")

    if stream:
        print("\n[TEST] ----- Streaming response -----")
        events: List[str] = []
        async for event in runtime.chat_stream(
            query=query,
            session_id=session_id,
            tenant_id=tenant_id,
            user_id="test-user",
        ):
            print(f"[STREAM] {event.strip()}")
            events.append(event)
        print("[TEST] ----- End of stream -----")
        return {"events": events}
    else:
        result = await runtime.chat(
            query=query,
            session_id=session_id,
            tenant_id=tenant_id,
            user_id="test-user",
        )
        print("\n[TEST] ----- Non-streaming result -----")
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        print("[TEST] ----- End of result -----")
        return result


def analyze_result(result: Dict[str, Any]) -> None:
    print("\n[ANALYSIS] Validating interaction...")

    finish_reason = result.get("finish_reason")
    tool_calls = result.get("tool_calls", [])
    answer = result.get("answer", "")
    session_id = result.get("session_id")
    agent_name = result.get("agent_name")

    assert agent_name == "test_default", f"Unexpected agent_name: {agent_name}"
    assert session_id.startswith("test-session-001"), f"Unexpected session_id: {session_id}"
    assert finish_reason == "stop", f"Expected finish_reason=stop, got {finish_reason}"
    assert len(tool_calls) == 1, f"Expected exactly 1 tool call, got {len(tool_calls)}"

    tc = tool_calls[0]
    assert tc.get("name") == "Read", f"Expected Read tool, got {tc.get('name')}"
    args = tc.get("args", {})
    assert args.get("file_path") == "/Users/lu/code/code/py/autofill/app/services/agent/agent_loop.py"
    assert args.get("limit") == 5

    assert "最终回答" in answer or "工具返回结果" in answer, f"Unexpected final answer: {answer}"

    print("[ANALYSIS] ✅ All assertions passed")


async def main():
    # Non-streaming test
    result = await run_test(stream=False, session_suffix="")
    analyze_result(result)

    # Streaming test
    stream_result = await run_test(stream=True, session_suffix="-stream")
    events = stream_result.get("events", [])
    content_events = [e for e in events if '"type": "content"' in e]
    done_events = [e for e in events if '"type": "done"' in e]
    tool_use_events = [e for e in events if '"type": "tool_use"' in e]

    print("\n[ANALYSIS STREAM] Validating streaming interaction...")
    assert tool_use_events, "Expected at least one tool_use event in stream"
    assert done_events, "Expected at least one done event in stream"
    print("[ANALYSIS STREAM] ✅ Streaming assertions passed")


if __name__ == "__main__":
    asyncio.run(main())
