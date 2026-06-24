#!/usr/bin/env python3
"""
通用 Agent MCP 流式测试脚本

功能：
1. 通过参数设置 query 测试 agent
2. 生成/复用 session_id 并持久化到文件
3. 支持强制开启新 session
4. 支持把 query 和流式结果写入文件
5. 支持两轮对话测试：先生成递归算法文件，再执行它
"""
import argparse
import asyncio
import json
import os
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

DEFAULT_SESSION_FILE = os.path.expanduser("~/.trae_agent_test_session")
DEFAULT_AGENT = "default"
DEFAULT_USER_ID = "test_user"


def parse_args():
    parser = argparse.ArgumentParser(description="通用 Agent MCP 流式测试脚本")
    parser.add_argument("-q", "--query", action="append", help="要发送的 query，可多次指定实现多轮")
    parser.add_argument("-s", "--session-file", default=DEFAULT_SESSION_FILE,
                        help="session_id 持久化文件路径")
    parser.add_argument("-n", "--new-session", action="store_true",
                        help="强制开启新 session，替换旧的 session_id")
    parser.add_argument("-o", "--output", default=None,
                        help="把 query 和流式结果写入文件（追加模式）")
    parser.add_argument("-a", "--agent-name", default=DEFAULT_AGENT, help="agent 名称")
    parser.add_argument("-u", "--user-id", default=DEFAULT_USER_ID, help="用户 ID")
    parser.add_argument("-m", "--max-iterations", type=int, default=20, help="最大迭代次数")
    parser.add_argument("-t", "--two-round", action="store_true",
                        help="执行两轮对话测试：先写递归算法文件，再执行它")
    return parser.parse_args()


def load_or_create_session_id(session_file, new_session=False):
    if not new_session and os.path.exists(session_file):
        with open(session_file, "r", encoding="utf-8") as f:
            session_id = f.read().strip()
        if session_id:
            print(f"复用已有 session: {session_id}")
            return session_id
    session_id = f"agent_test_{int(time.time())}"
    save_session_id(session_file, session_id)
    print(f"创建新 session: {session_id}")
    return session_id


def save_session_id(session_file, session_id):
    parent = os.path.dirname(os.path.abspath(session_file))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(session_file, "w", encoding="utf-8") as f:
        f.write(session_id)


async def call_agent_stream(
    query,
    session_id,
    agent_name=DEFAULT_AGENT,
    user_id=DEFAULT_USER_ID,
    max_iterations=20,
    output_fp=None,
):
    payload = {
        "query": query,
        "agent_name": agent_name,
        "session_id": session_id,
        "user_id": user_id,
        "stream": True,
        "max_iterations": max_iterations,
    }

    print(f"\n用户输入: {query}")
    print(f"会话ID: {session_id}")
    print("-" * 70)

    if output_fp:
        output_fp.write("\n\n===== 新对话 =====\n")
        output_fp.write(f"Session ID: {session_id}\n")
        output_fp.write(f"Query: {query}\n")
        output_fp.write("-" * 70 + "\n")

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
    tool_calls = []

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                AGENT_CHAT_URL,
                headers=HEADERS,
                json=payload
            ) as response:
                print(f"HTTP 状态码: {response.status_code}")

                if response.status_code != 200:
                    print(f"❌ HTTP 错误: {response.status_code}")
                    text = await response.aread()
                    print(f"响应: {text.decode()[:500]}")
                    if output_fp:
                        output_fp.write(f"❌ HTTP 错误: {response.status_code}\n")
                        output_fp.write(text.decode()[:500] + "\n")
                    return False, "", ""

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue

                    event_type = data.get("type")

                    if event_type == "start":
                        msg = f"[事件] 对话开始 - ID: {data.get('session_id')}\n"
                        print(msg, end="")
                        if output_fp:
                            output_fp.write(msg)

                    elif event_type == "content":
                        content = data.get("content", "")
                        full_answer += content
                        event_count["content"] += 1
                        print(content, end="", flush=True)
                        if output_fp:
                            output_fp.write(content)

                    elif event_type == "reasoning":
                        reasoning = data.get("content", "")
                        full_reasoning += reasoning
                        event_count["reasoning"] += 1
                        print(f"\n[reasoning] {reasoning}", end="", flush=True)
                        if output_fp:
                            output_fp.write(f"\n[reasoning] {reasoning}")

                    elif event_type == "tool_start":
                        event_count["tool_start"] += 1
                        msg = f"\n[事件] 开始工具调用 - 数量: {data.get('count')}\n"
                        print(msg, end="")
                        if output_fp:
                            output_fp.write(msg)

                    elif event_type == "tool_use":
                        event_count["tool_use"] += 1
                        tool_name = data.get("name")
                        arguments = data.get("arguments", {})
                        tool_calls.append({"name": tool_name, "arguments": arguments})
                        msg = f"\n[工具] {tool_name}\n"
                        print(msg, end="")
                        if output_fp:
                            output_fp.write(msg)
                        if arguments:
                            args_str = json.dumps(arguments, ensure_ascii=False)[:500]
                            print(f"       参数: {args_str}...")
                            if output_fp:
                                output_fp.write(f"       参数: {args_str}...\n")

                    elif event_type == "tool_result":
                        event_count["tool_result"] += 1
                        tool_name = data.get("name")
                        status = data.get("status")
                        result = data.get("result", "")
                        msg = f"[结果] {tool_name} - 状态: {status}\n"
                        print(msg, end="")
                        if output_fp:
                            output_fp.write(msg)
                        if result:
                            result_str = json.dumps(result, ensure_ascii=False)[:500]
                            print(f"       结果: {result_str}...")
                            if output_fp:
                                output_fp.write(f"       结果: {result_str}...\n")

                    elif event_type == "error":
                        event_count["error"] += 1
                        error_msg = data.get("error", "Unknown error")
                        msg = f"\n❌ [错误] {error_msg[:300]}...\n"
                        print(msg, end="")
                        if output_fp:
                            output_fp.write(msg)

                    elif event_type == "done":
                        event_count["done"] += 1
                        finish_reason = data.get("finish_reason", "")
                        msg = f"\n[事件] 对话完成 - finish_reason: {finish_reason}\n"
                        print(msg, end="")
                        if output_fp:
                            output_fp.write(msg)

    except httpx.ConnectError as e:
        msg = f"\n❌ 无法连接到 agent 后端: {AGENT_CHAT_URL}，请确认服务已启动\n"
        print(msg)
        if output_fp:
            output_fp.write(msg)
        return False, "", ""
    except Exception as e:
        msg = f"\n❌ 请求异常: {type(e).__name__}: {e}\n"
        print(msg)
        if output_fp:
            output_fp.write(msg)
        return False, "", ""

    print("\n" + "-" * 70)
    stats = (f"事件统计: 内容片段={event_count['content']}, 推理片段={event_count['reasoning']}, "
             f"工具调用={event_count['tool_use']}, 完成={event_count['done']}, 错误={event_count['error']}")
    print(stats)

    if output_fp:
        output_fp.write("-" * 70 + "\n")
        output_fp.write(stats + "\n")
        output_fp.write(f"Finish reason: {finish_reason}\n")
        output_fp.write(f"完整回答:\n{full_answer}\n")

    return True, full_answer, finish_reason


async def run_two_round_test(session_id, args, output_fp=None):
    """两轮对话测试：先写递归算法文件，再执行它。"""
    round1_query = ("请写一个计算斐波那契数列的简单递归算法 Python 文件，"
                    "保存到 /tmp/fibonacci.py，包含一个 fib(n) 函数和简单的调用示例")
    round2_query = "请执行 /tmp/fibonacci.py 文件，并告诉我输出结果"

    print("\n" + "=" * 70)
    print("第一轮：让 agent 写递归算法文件")
    print("=" * 70)
    ok1, answer1, finish1 = await call_agent_stream(
        round1_query, session_id, args.agent_name, args.user_id, args.max_iterations, output_fp
    )

    print("\n" + "=" * 70)
    print("第二轮：让 agent 执行刚生成的文件")
    print("=" * 70)
    ok2, answer2, finish2 = await call_agent_stream(
        round2_query, session_id, args.agent_name, args.user_id, args.max_iterations, output_fp
    )

    return ok1 and ok2, answer1, answer2


async def main():
    args = parse_args()

    if args.two_round:
        queries = []
    else:
        queries = args.query or []
        if not queries:
            print("请使用 -q/--query 指定 query，或使用 -t/--two-round 执行两轮测试")
            sys.exit(1)

    session_id = load_or_create_session_id(args.session_file, args.new_session)

    output_fp = None
    if args.output:
        parent = os.path.dirname(os.path.abspath(args.output))
        if parent:
            os.makedirs(parent, exist_ok=True)
        output_fp = open(args.output, "a", encoding="utf-8")
        print(f"输出将写入: {args.output}")

    try:
        if args.two_round:
            success, _, _ = await run_two_round_test(session_id, args, output_fp)
        else:
            success = True
            for query in queries:
                ok, _, _ = await call_agent_stream(
                    query, session_id, args.agent_name, args.user_id, args.max_iterations, output_fp
                )
                success = success and ok
    finally:
        if output_fp:
            output_fp.close()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
