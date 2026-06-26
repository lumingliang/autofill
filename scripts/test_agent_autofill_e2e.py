#!/usr/bin/env python3
"""
端到端 Agent 自动填单测试

调用 autofill Agent，让它自动识别 autofill-form skill，
并通过 run_mcp 依次调用 mcp_form_field / mcp_rule_engine 完成表单填写。
"""
import asyncio
import json
import time

from app.services.agent import chat
from app.services.agent.trace import get_trace_logger


USER_QUERY = (
    "帮我填一个 400 汽车客服工单。客户张三，电话 13800000001，"
    "车辆 SUV，车架号 LSV1234567890，行驶里程 5000 公里，车辆无法启动，"
    "位置北京市朝阳区，需要标准拖车，期望 30 分钟内到达，车上 1 人，"
    "已安排拖车预计 15 分钟到 4S 店，客户情绪稳定。"
)


async def main():
    session_id = f"autofill_e2e_{int(time.time())}"
    print(f"[session_id] {session_id}")
    print("[user_query]", USER_QUERY)
    print("=" * 60)

    result = await chat(
        agent_name="autofill",
        query=USER_QUERY,
        session_id=session_id,
        user_id="e2e_tester",
    )

    print("\n[result]")
    print(json.dumps({
        "trace_id": result.get("trace_id"),
        "session_id": result.get("session_id"),
        "finish_reason": result.get("finish_reason"),
        "tool_calls": [
            {"name": tc.get("name"), "args": tc.get("args")}
            for tc in result.get("tool_calls", [])
        ],
        "answer": result.get("answer", "")[:800],
    }, ensure_ascii=False, indent=2))

    answer = result.get("answer", "")
    form_id = None
    for part in (answer, json.dumps(result.get("tool_calls", []))):
        for token in part.replace('"', ' ').replace("'", " ").replace(":", " ").split():
            if token.startswith("FORM") or token.isdigit() and len(token) >= 6:
                form_id = token
                break
        if form_id:
            break

    print(f"\n[form_id] {form_id or '未明确提取到，请检查 answer'}")

    logger = get_trace_logger()
    steps = logger.get_steps(result.get("trace_id"))
    print("\n[trace steps]")
    for s in steps:
        print(
            f"step={s['step_index']:02d} node={s['node_name']:<18} "
            f"latency_ms={s['latency_ms']:>8}"
        )

    if result.get("finish_reason") == "stop" and form_id:
        print("\n✅ 自动填单端到端测试通过")
    else:
        print("\n❌ 自动填单端到端测试未通过，请检查链路日志")


if __name__ == "__main__":
    asyncio.run(main())
