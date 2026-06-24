#!/usr/bin/env python3
"""
Agent 端到端测试脚本 - 流式多工具调用 / TodoWrite 场景

验证目标：
1. 大模型在单轮中返回多个工具调用（Multi-tool parallel calls）
2. 大模型调用 TodoWrite 做任务规划
3. 流式实时返回 content 和 reasoning
4. 客户端完整捕获所有 tool_start / tool_use / tool_result 事件

建议 query 设计思路：
- 明确请求"先创建 TODO 列表"
- 明确要求"并行执行"多个独立工具调用
- 给每个工具调用独立的上下文，降低 LLM 顺序执行的倾向
"""
import asyncio
import json
import sys
import time
import httpx

BASE_URL = "http://127.0.0.1:9999"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}
AGENT_CHAT_URL = f"{BASE_URL}/api/v1/open/agent/v2/chat"

# 设计用于触发 TodoWrite + 多工具并行的 query
MULTI_TOOL_QUERY = """\
我有一个复杂任务，需要你分步骤完成。

请先用 TodoWrite 创建一个任务列表，规划以下工作：
1. 使用 Glob 查找项目根目录下所有 Python 脚本文件（*.py）
2. 使用 RunCommand 执行 `git status --short` 查看当前仓库状态
3. 使用 Read 读取 README.md 的前 30 行
4. 总结以上信息并简要说明项目结构和当前状态

注意：第 1-3 步彼此独立，请在规划完成后尽量并行执行它们，最后给出总结。\
"""


async def test_multi_tool_stream():
    print("\n" + "=" * 80)
    print("测试：流式多工具调用 + TodoWrite 场景")
    print("=" * 80)

    session_id = f"test_multi_tool_{int(time.time())}"
    payload = {
        "query": MULTI_TOOL_QUERY,
        "agent_name": "default",
        "session_id": session_id,
        "user_id": "test_user",
        "stream": True,
        "max_iterations": 50
    }

    print(f"\n会话ID: {session_id}")
    print(f"Query:\n{MULTI_TOOL_QUERY}\n")
    print("-" * 80)

    full_answer = ""
    full_reasoning = ""
    finish_reason = ""
    reasoning_parts = []
    content_parts = []
    tool_start_events = []
    tool_use_events = []
    tool_result_events = []
    error_events = []

    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream(
            "POST",
            AGENT_CHAT_URL,
            headers=HEADERS,
            json=payload
        ) as response:
            print(f"状态码: {response.status_code}\n")
            if response.status_code != 200:
                text = await response.aread()
                print(f"❌ HTTP 错误: {response.status_code}\n{text.decode()[:500]}")
                return False

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    data = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue

                event_type = data.get("type")

                if event_type == "start":
                    print(f"[start] session_id={data.get('session_id')} agent={data.get('agent_name')}")

                elif event_type == "content":
                    content = data.get("content", "")
                    content_parts.append(content)
                    full_answer += content
                    # 实时连续输出完整内容，不换行，立即刷新
                    print(content, end="", flush=True)

                elif event_type == "reasoning":
                    reasoning = data.get("content", "")
                    reasoning_parts.append(reasoning)
                    full_reasoning += reasoning
                    # 实时连续输出完整推理内容
                    print(f"\n[reasoning] {reasoning}", end="", flush=True)

                elif event_type == "tool_start":
                    count = data.get("count", 0)
                    tool_start_events.append(count)
                    print(f"\n[tool_start] 本批工具调用数量: {count}")

                elif event_type == "tool_use":
                    tool_use_events.append(data)
                    name = data.get("name", "")
                    args = data.get("arguments", {})
                    args_short = json.dumps(args, ensure_ascii=False)[:200]
                    print(f"[tool_use] {name} | args: {args_short}...")

                elif event_type == "tool_result":
                    tool_result_events.append(data)
                    print(f"[tool_result] {data.get('name')} status={data.get('status')}")

                elif event_type == "error":
                    error_events.append(data)
                    print(f"\n❌ [error] {data.get('error', 'Unknown error')[:300]}...")

                elif event_type == "done":
                    finish_reason = data.get("finish_reason", "")
                    print(f"\n[done] finish_reason={finish_reason}")

    print("\n" + "=" * 80)
    print("事件统计:")
    print(f"  content 片段数: {len(content_parts)}")
    print(f"  reasoning 片段数: {len(reasoning_parts)}")
    print(f"  tool_start 次数: {len(tool_start_events)} (每批数量: {tool_start_events})")
    print(f"  tool_use 次数: {len(tool_use_events)}")
    print(f"  tool_result 次数: {len(tool_result_events)}")
    print(f"  error 次数: {len(error_events)}")

    # 验证
    checks = []

    # 1. 至少有一个 tool_start 事件包含 >=2 个工具调用（多工具并行）
    multi_tool_batches = [c for c in tool_start_events if c >= 2]
    if multi_tool_batches:
        print(f"\n✅ 检测到多工具并行调用批次: {multi_tool_batches}")
        checks.append(True)
    else:
        print("\n⚠️ 未检测到单轮 >=2 个工具调用（LLM 可能顺序执行）")
        checks.append(False)

    # 2. 检测 TodoWrite 调用
    todo_calls = [e for e in tool_use_events if e.get("name") == "TodoWrite"]
    if todo_calls:
        print(f"✅ 检测到 TodoWrite 调用: {len(todo_calls)} 次")
        checks.append(True)
    else:
        print("⚠️ 未检测到 TodoWrite 调用")
        checks.append(False)

    # 3. 流式 content 非空
    if full_answer and len(full_answer) > 10:
        print(f"✅ 收到有效回答: {len(full_answer)} 字符")
        checks.append(True)
    else:
        print(f"⚠️ 回答较短: {full_answer[:100]}")
        checks.append(False)

    # 4. tool_use 与 tool_result 数量一致
    if len(tool_use_events) == len(tool_result_events) and len(tool_use_events) > 0:
        print(f"✅ tool_use/tool_result 成对出现: {len(tool_use_events)} 对")
        checks.append(True)
    else:
        print(f"⚠️ tool_use={len(tool_use_events)}, tool_result={len(tool_result_events)}")
        checks.append(False)

    # 5. 正常结束
    if finish_reason == "stop":
        print(f"✅ 正常结束: finish_reason='stop'")
        checks.append(True)
    else:
        print(f"⚠️ 结束原因: finish_reason='{finish_reason}'")
        checks.append(False)

    print(f"\n{'-' * 80}")
    print("完整回答内容:")
    print('-' * 80)
    print(full_answer)
    if full_reasoning:
        print(f"\n{'-' * 80}")
        print("完整推理内容:")
        print('-' * 80)
        print(full_reasoning)

    passed = sum(checks)
    total = len(checks)
    print("\n" + "=" * 80)
    print(f"测试结果: {passed}/{total} 通过")

    # 打印所有工具调用名称序列，方便人工检查
    tool_names = [e.get("name") for e in tool_use_events]
    print(f"工具调用序列: {tool_names}")

    return passed == total


async def main():
    print("=" * 80)
    print("Agent 流式多工具调用测试")
    print(f"API: {AGENT_CHAT_URL}")
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        success = await test_multi_tool_stream()
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        success = False

    print("\n" + "=" * 80)
    if success:
        print("✅ 多工具流式测试通过")
    else:
        print("❌ 多工具流式测试未通过")
        print("\n提示:")
        print("  - 若未触发 TodoWrite，可在 query 中更明确地要求'先用 TodoWrite 规划'")
        print("  - 若未触发多工具并行，可在 query 中强调'这些步骤彼此独立，请并行执行'")
        print("  - 不同模型对并行工具调用的支持程度不同")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
