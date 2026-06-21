#!/usr/bin/env python3
"""
Agent 端到端测试脚本 - 简化版（适配配置化 Agent 架构）

测试场景：道路救援填单
验证：
1. Agent 能够自动识别填单意图并调用 autofill-form skill
2. Skill 内容正确加载到对话上下文
3. Agent 按照 SKILL.md 指导执行填单流程
4. 终止条件为 finish_reason="stop"
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


async def test_roadside_rescue_form_filling():
    """
    测试场景：道路救援填单

    用户输入包含道路救援相关信息，期望 Agent：
    1. 识别填单意图，调用 autofill-form skill
    2. 按照 Skill 指导执行 CLI 脚本获取字段、选项
    3. 自动选择事件类型并提交表单
    4. 返回 finish_reason="stop"
    """
    print("\n" + "=" * 70)
    print("测试：道路救援填单场景")
    print("=" * 70)

    session_id = f"test_rescue_{int(time.time())}"

    payload = {
        "query": "我的车在高速公路抛锚了，需要紧急拖车。我叫李四，电话13900139000，车在G15沈海高速K1234处。请帮我填单记录。",
        "agent_name": "autofill",
        "session_id": session_id,
        "user_id": "test_user",
        "tenant_id": "default",
        "stream": False,
        "max_iterations": 50
    }

    print(f"\n用户输入: {payload['query']}")
    print(f"会话ID: {session_id}")
    print(f"Agent: {payload['agent_name']}")

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(AGENT_CHAT_URL, headers=HEADERS, json=payload)

        print(f"\n状态码: {response.status_code}")

        if response.status_code != 200:
            print(f"❌ HTTP 错误: {response.status_code}")
            print(f"响应: {response.text}")
            return False

        result = response.json()

        if result.get("code") != 200:
            print(f"❌ 业务错误: {result.get('msg')}")
            return False

        data = result.get("data", {})
        tool_calls = data.get("tool_calls", [])
        finish_reason = data.get("finish_reason", "")
        answer = data.get("answer", "")
        resp_session_id = data.get("session_id", "")
        resp_agent_name = data.get("agent_name", "")

        print(f"\n✅ 请求成功")
        print(f"   返回会话ID: {resp_session_id}")
        print(f"   返回Agent: {resp_agent_name}")
        print(f"   结束原因: {finish_reason}")
        print(f"   回答: {answer[:200]}...")
        print(f"\n   工具调用记录 ({len(tool_calls)} 次):")

        # 验证关键点
        skill_triggered = False
        runcommand_count = 0
        expected_cli_calls = [
            "get_field.py",
            "get_field_rules.py",
            "submit_form.py"
        ]
        cli_calls_found = []

        for i, tc in enumerate(tool_calls, 1):
            tool_name = tc.get('name', '')
            tool_args = tc.get('args', {})
            print(f"   [{i}] {tool_name}")

            if tool_name == 'Skill':
                skill_triggered = True
                skill_result = tc.get('result', '')
                try:
                    result_data = json.loads(skill_result)
                    print(f"       Skill 结果类型: {result_data.get('type', 'unknown')}")
                    if result_data.get('type') == 'skill_activated':
                        print(f"       ✅ Skill 成功激活: {result_data.get('skill_name', '')}")
                except Exception:
                    print(f"       结果: {str(skill_result)[:100]}...")

            elif tool_name == 'RunCommand':
                runcommand_count += 1
                command = tool_args.get('command', '')
                print(f"       命令: {command[:80]}...")

                # 检查是否调用了预期的 CLI 脚本
                for cli in expected_cli_calls:
                    if cli in command:
                        cli_calls_found.append(cli)

        # 验证结果
        print("\n" + "-" * 50)
        print("验证结果:")

        checks = []

        # 检查1: 会话隔离
        if resp_session_id == session_id:
            print("   ✅ 会话ID一致")
            checks.append(True)
        else:
            print(f"   ⚠️ 会话ID不一致: 请求={session_id}, 返回={resp_session_id}")
            checks.append(False)

        # 检查2: Skill 是否被触发
        if skill_triggered:
            print("   ✅ Skill 工具已触发")
            checks.append(True)
        else:
            print("   ❌ Skill 工具未被触发")
            checks.append(False)

        # 检查3: 是否有 CLI 脚本调用
        if runcommand_count > 0:
            print(f"   ✅ RunCommand 调用次数: {runcommand_count}")
            checks.append(True)
        else:
            print("   ❌ 没有 RunCommand 调用")
            checks.append(False)

        # 检查4: 是否调用了预期的 CLI 脚本
        unique_cli_calls = list(set(cli_calls_found))
        if "get_field_rules.py" in unique_cli_calls:
            print("   ✅ 规则获取脚本已调用")
            checks.append(True)
        else:
            print("   ❌ 规则获取脚本未调用 (get_field_rules.py)")
            checks.append(False)

        if len(unique_cli_calls) >= 2:
            print(f"   ✅ 关键 CLI 脚本调用: {', '.join(unique_cli_calls)}")
            checks.append(True)
        else:
            print(f"   ⚠️ CLI 脚本调用不足: {unique_cli_calls}")
            checks.append(False)

        # 检查5: 终止条件
        if finish_reason == "stop":
            print(f"   ✅ 终止条件正确: finish_reason='stop'")
            checks.append(True)
        else:
            print(f"   ⚠️ 终止条件: finish_reason='{finish_reason}'")
            checks.append(False)

        # 检查6: 有回答内容
        if answer and len(answer) > 10:
            print(f"   ✅ 有有效回答内容 ({len(answer)} 字符)")
            checks.append(True)
        else:
            print(f"   ⚠️ 回答内容较短: {answer}")
            checks.append(False)

        passed = sum(checks)
        total = len(checks)

        print("\n" + "=" * 70)
        print(f"测试结果: {passed}/{total} 通过")

        if passed == total:
            print("道路救援填单测试通过!")
            return True
        else:
            print("⚠️ 部分检查未通过")
            return False


async def run_test():
    """运行测试"""
    print("\n" + "=" * 70)
    print("Agent 端到端测试 - 简化版")
    print("=" * 70)
    print(f"API URL: {AGENT_CHAT_URL}")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        success = await test_roadside_rescue_form_filling()
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        success = False

    print("\n" + "=" * 70)
    if success:
        print("✅ 测试通过")
        print("\n说明:")
        print("   - Agent 正确识别了填单意图")
        print("   - autofill-form Skill 被成功触发")
        print("   - CLI 脚本被正确调用执行填单流程")
        print("   - 终止条件为 finish_reason='stop'")
    else:
        print("❌ 测试未通过")
        print("\n请检查:")
        print("   1. 后端服务是否运行 (python run.py)")
        print("   2. LiteLLM 网关是否运行 (http://localhost:4000)")
        print("   3. config.toml [agent] 模型配置是否正确")
        print("   4. autofill-form skill 文件是否存在且内容正确")
        print("   5. Agent 'autofill' 是否正确注册")

    return success


if __name__ == "__main__":
    success = asyncio.run(run_test())
    sys.exit(0 if success else 1)
