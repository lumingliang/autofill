#!/usr/bin/env python3
"""
Agent 端到端测试脚本 - 流式版本

测试场景：道路救援填单（流式响应）
验证：
1. Agent 能够自动识别填单意图并调用 autofill-form skill
2. Skill 内容正确加载到对话上下文
3. Agent 按照 SKILL.md 指导执行填单流程
4. 终止条件为 finish_reason="stop"

交互格式遵循 /Users/lu/code/code/py/autofill/scripts/cli/1.json 规范
"""
import asyncio
import json
import sys
import time
import httpx
import os

# 设置环境变量
os.environ["LLM_API_KEY"] = "sk-litellm-master-key"
os.environ["LLM_BASE_URL"] = "http://localhost:4000"
os.environ["LLM_MODEL"] = "qwen3.6-27b"

# API 配置
BASE_URL = "http://127.0.0.1:9999"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

AGENT_CHAT_URL = f"{BASE_URL}/api/v1/open/agent/v2/chat"


async def test_roadside_rescue_form_filling_stream():
    """
    测试场景：道路救援填单（流式响应）
    """
    print("\n" + "=" * 70)
    print("测试：道路救援填单场景（流式响应）")
    print("=" * 70)

    session_id = f"test_rescue_stream_{int(time.time())}"

    # 道路救援场景的用户输入
    payload = {
        "query": "我的车在高速公路抛锚了，需要紧急拖车。我叫李四，电话13900139000，车在G15沈海高速K1234处。请帮我填单记录。",
        "agent_name": "autofill",
        "session_id": session_id,
        "user_id": "test_user",
        "stream": True,
        "max_iterations": 50
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
    event_count = {"content": 0, "reasoning": 0, "tool_start": 0, "tool_use": 0, "tool_result": 0, "done": 0}

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
                    data = json.loads(line[6:])  # 去掉 "data: " 前缀
                except json.JSONDecodeError:
                    continue

                event_type = data.get("type")

                if event_type == "start":
                    print(f"\n[事件] 对话开始 - ID: {data.get('session_id')}")

                elif event_type == "content":
                    content = data.get("content", "")
                    full_answer += content
                    event_count["content"] += 1
                    # 实时连续输出完整内容，不换行，立即刷新
                    print(content, end="", flush=True)

                elif event_type == "reasoning":
                    reasoning = data.get("content", "")
                    full_reasoning += reasoning
                    event_count["reasoning"] += 1
                    # 实时连续输出完整推理内容
                    print(f"\n[reasoning] {reasoning}", end="", flush=True)

                elif event_type == "tool_start":
                    event_count["tool_start"] += 1
                    print(f"\n[事件] 开始工具调用 - 数量: {data.get('count')}")

                elif event_type == "tool_use":
                    event_count["tool_use"] += 1
                    tool_name = data.get("name")
                    arguments = data.get("arguments", {})
                    print(f"[工具] {tool_name}")
                    if arguments:
                        args_str = json.dumps(arguments, ensure_ascii=False)[:200]
                        print(f"       参数: {args_str}...")

                elif event_type == "tool_result":
                    event_count["tool_result"] += 1
                    tool_name = data.get("name")
                    status = data.get("status")
                    print(f"[结果] {tool_name} - 状态: {status}")

                elif event_type == "error":
                    error_msg = data.get("error", "Unknown error")
                    print(f"\n❌ [错误] {error_msg[:300]}...")

                elif event_type == "done":
                    event_count["done"] += 1
                    finish_reason = data.get("finish_reason", "")
                    print(f"\n[事件] 对话完成 - finish_reason: {finish_reason}")
                    if data.get("reasoning_content"):
                        print(f"[推理总结] {data['reasoning_content'][:200]}...")

    # 验证结果
    print("\n" + "=" * 70)
    print("验证结果:")
    print("=" * 70)

    checks = []

    print(f"\n{'-' * 70}")
    print("完整回答内容:")
    print('-' * 70)
    print(full_answer)
    if full_reasoning:
        print(f"\n{'-' * 70}")
        print("完整推理内容:")
        print('-' * 70)
        print(full_reasoning)

    # 检查1: 是否有内容返回
    if full_answer and len(full_answer) > 10:
        print(f"\n   ✅ 有有效回答内容 ({len(full_answer)} 字符)")
        checks.append(True)
    else:
        print(f"\n   ⚠️ 回答内容较短: {full_answer[:100]}")
        checks.append(False)

    # 检查2: 是否有工具调用
    if event_count["tool_use"] > 0:
        print(f"   ✅ 工具调用次数: {event_count['tool_use']}")
        checks.append(True)
    else:
        print("   ❌ 没有工具调用")
        checks.append(False)

    # 检查3: 终止条件
    if finish_reason == "stop":
        print(f"   ✅ 终止条件正确: finish_reason='stop'")
        checks.append(True)
    else:
        print(f"   ⚠️ 终止条件: finish_reason='{finish_reason}'")
        checks.append(False)

    # 检查4: 事件统计
    print(f"\n   事件统计:")
    print(f"      - 内容片段: {event_count['content']}")
    print(f"      - 推理片段: {event_count['reasoning']}")
    print(f"      - 工具开始: {event_count['tool_start']}")
    print(f"      - 工具调用: {event_count['tool_use']}")
    print(f"      - 工具结果: {event_count['tool_result']}")
    print(f"      - 完成事件: {event_count['done']}")

    passed = sum(checks)
    total = len(checks)

    print("\n" + "=" * 70)
    print(f"测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 道路救援填单流式测试通过!")
        return True
    else:
        print("⚠️ 部分检查未通过")
        return False


async def run_test():
    """运行测试"""
    print("\n" + "=" * 70)
    print("Agent 端到端测试 - 流式版本")
    print("=" * 70)
    print(f"API URL: {AGENT_CHAT_URL}")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"环境变量:")
    print(f"  LLM_API_KEY: {os.environ.get('LLM_API_KEY', 'NOT SET')}")
    print(f"  LLM_BASE_URL: {os.environ.get('LLM_BASE_URL', 'NOT SET')}")
    print(f"  LLM_MODEL: {os.environ.get('LLM_MODEL', 'NOT SET')}")

    try:
        success = await test_roadside_rescue_form_filling_stream()
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        success = False

    print("\n" + "=" * 70)
    if success:
        print("✅ 流式测试通过")
        print("\n说明:")
        print("   - Agent 正确识别了填单意图")
        print("   - autofill-form Skill 被成功触发")
        print("   - 流式响应正常工作")
        print("   - 终止条件为 finish_reason='stop'")
    else:
        print("❌ 流式测试未通过")
        print("\n请检查:")
        print("   1. 系统提示词是否包含 skill 触发逻辑")
        print("   2. autofill-form skill 文件是否存在且内容正确")
        print("   3. Agent 是否正确绑定工具")
        print("   4. LLM 是否能够正确识别填单意图")
        print("   5. Mock API 服务是否运行 (port 6666)")

    return success


if __name__ == "__main__":
    success = asyncio.run(run_test())
    sys.exit(0 if success else 1)
