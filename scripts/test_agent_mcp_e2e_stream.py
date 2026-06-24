#!/usr/bin/env python3
"""
Agent MCP 端到端测试脚本 - 流式版本

测试场景：让 default agent 通过 MCP 工具查看 seekdb 数据库中的表
验证：
1. Agent 能根据系统提示词中的 MCP section 识别可用 MCP 服务器
2. Agent 在需要时调用 RunMCP 工具
3. RunMCP 成功返回 seekdb 数据表信息
4. 终止条件为 finish_reason="stop"

交互格式遵循 /Users/lu/code/code/py/autofill/scripts/cli/1.json 规范
"""
import asyncio
import json
import sys
import time
import httpx

# API 配置
BASE_URL = "http://127.0.0.1:9999"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

AGENT_CHAT_URL = f"{BASE_URL}/api/v1/open/agent/v2/chat"


async def test_agent_mcp_seekdb_tables():
    """测试：让 agent 使用 MCP 查看 seekdb 中的表"""
    print("\n" + "=" * 70)
    print("测试：Agent 通过 MCP 查看 seekdb 数据表")
    print("=" * 70)

    session_id = f"test_mcp_seekdb_stream_{int(time.time())}"

    payload = {
        "query": "请使用 MCP 工具查看 seekdb 数据库 autofill 库里有哪些表，并简单列出表名",
        "agent_name": "default",
        "session_id": session_id,
        "user_id": "test_user",
        "stream": True,
        "max_iterations": 20
    }

    print(f"\n用户输入: {payload['query']}")
    print(f"会话ID: {session_id}")
    print(f"\n{'-' * 70}")
    print("开始流式接收响应...")
    print('-' * 70)

    tool_calls = []
    full_answer = ""
    full_reasoning = ""
    finish_reason = ""
    event_count = {
        "content": 0,
        "reasoning": 0,
        "tool_start": 0,
        "tool_use": 0,
        "tool_result": 0,
        "done": 0,
        "error": 0,
    }
    runmcp_called = False
    runmcp_success = False

    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream(
            "POST",
            AGENT_CHAT_URL,
            headers=HEADERS,
            json=payload
        ) as response:
            print(f"\n状态码: {response.status_code}")

            if response.status_code != 200:
                print(f"❌ HTTP 错误: {response.status_code}")
                text = await response.aread()
                print(f"响应: {text.decode()[:500]}")
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
                    print(f"\n[事件] 对话开始 - ID: {data.get('session_id')}")

                elif event_type == "content":
                    content = data.get("content", "")
                    full_answer += content
                    event_count["content"] += 1
                    print(content, end="", flush=True)

                elif event_type == "reasoning":
                    reasoning = data.get("content", "")
                    full_reasoning += reasoning
                    event_count["reasoning"] += 1
                    print(f"\n[reasoning] {reasoning}", end="", flush=True)

                elif event_type == "tool_start":
                    event_count["tool_start"] += 1
                    print(f"\n[事件] 开始工具调用 - 数量: {data.get('count')}")

                elif event_type == "tool_use":
                    event_count["tool_use"] += 1
                    tool_name = data.get("name")
                    arguments = data.get("arguments", {})
                    print(f"\n[工具] {tool_name}")
                    if tool_name == "RunMCP":
                        runmcp_called = True
                    if arguments:
                        args_str = json.dumps(arguments, ensure_ascii=False)[:300]
                        print(f"       参数: {args_str}...")

                elif event_type == "tool_result":
                    event_count["tool_result"] += 1
                    tool_name = data.get("name")
                    status = data.get("status")
                    result = data.get("result", "")
                    print(f"[结果] {tool_name} - 状态: {status}")
                    if tool_name == "RunMCP" and status == "done":
                        runmcp_success = True
                    if result:
                        result_str = json.dumps(result, ensure_ascii=False)[:300]
                        print(f"       结果: {result_str}...")

                elif event_type == "error":
                    event_count["error"] += 1
                    error_msg = data.get("error", "Unknown error")
                    print(f"\n❌ [错误] {error_msg[:300]}...")

                elif event_type == "done":
                    event_count["done"] += 1
                    finish_reason = data.get("finish_reason", "")
                    print(f"\n[事件] 对话完成 - finish_reason: {finish_reason}")

    # 验证结果
    print("\n" + "=" * 70)
    print("验证结果:")
    print("=" * 70)

    checks = []

    if full_answer and len(full_answer) > 10:
        print(f"\n   ✅ 有有效回答内容 ({len(full_answer)} 字符)")
        checks.append(True)
    else:
        print(f"\n   ⚠️ 回答内容较短: {full_answer[:100]}")
        checks.append(False)

    if event_count["tool_use"] > 0:
        print(f"   ✅ 工具调用次数: {event_count['tool_use']}")
        checks.append(True)
    else:
        print("   ❌ 没有工具调用")
        checks.append(False)

    if runmcp_called:
        print("   ✅ Agent 调用了 RunMCP 工具")
        checks.append(True)
    else:
        print("   ❌ Agent 未调用 RunMCP 工具")
        checks.append(False)

    if runmcp_success:
        print("   ✅ RunMCP 工具调用成功")
        checks.append(True)
    else:
        print("   ❌ RunMCP 工具调用未成功")
        checks.append(False)

    if finish_reason == "stop":
        print(f"   ✅ 终止条件正确: finish_reason='stop'")
        checks.append(True)
    else:
        print(f"   ⚠️ 终止条件: finish_reason='{finish_reason}'")
        checks.append(False)

    print(f"\n   事件统计:")
    print(f"      - 内容片段: {event_count['content']}")
    print(f"      - 推理片段: {event_count['reasoning']}")
    print(f"      - 工具开始: {event_count['tool_start']}")
    print(f"      - 工具调用: {event_count['tool_use']}")
    print(f"      - 工具结果: {event_count['tool_result']}")
    print(f"      - 完成事件: {event_count['done']}")
    print(f"      - 错误事件: {event_count['error']}")

    passed = sum(checks)
    total = len(checks)

    print("\n" + "=" * 70)
    print(f"测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 Agent MCP 端到端测试通过!")
        return True
    else:
        print("❌ Agent MCP 端到端测试未通过")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_agent_mcp_seekdb_tables())
    sys.exit(0 if success else 1)
