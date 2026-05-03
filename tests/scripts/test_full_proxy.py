import asyncio
import httpx
import json

async def test_full_proxy():
    """测试完整的代理接口（结构化输出）"""
    async with httpx.AsyncClient() as client:


        # 2. 调用代理接口（使用应用的 API Key 认证）
        api_key = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"

        proxy_data = {
            "query": "请提取以下信息：姓名张三，年龄25岁，邮箱zhangsan@example.com",
            "tools": [
                {
                    "name": "extract_person_info",
                    "description": "提取人员信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "姓名"
                            },
                            "age": {
                                "type": "integer",
                                "description": "年龄"
                            },
                            "email": {
                                "type": "string",
                                "description": "邮箱"
                            }
                        },
                        "required": ["name", "age", "email"]
                    }
                }
            ],
            "system_prompt": "你是一个信息提取助手，请从用户输入中提取结构化信息。",
            "preferred_methods": ["with_structured_output", "custom_fc_non_stream", "json_parser"]
        }

        print("\nTesting proxy API with structured output...")
        print(f"Using API Key: {api_key[:10]}...")

        try:
            proxy_resp = await client.post(
                'http://localhost:9999/api/llm/proxy',
                json=proxy_data,
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=60
            )
            print(f'Proxy response status: {proxy_resp.status_code}')
            result = proxy_resp.json()
            print(f'Proxy response: {json.dumps(result, indent=2, ensure_ascii=False)}')

            if result.get('code') == 200:
                print("\n✓ Proxy API structured output test PASSED!")
                data = result.get('data', {})
                print(f"Method used: {data.get('method')}")
                print(f"Result data: {json.dumps(data.get('data'), indent=2, ensure_ascii=False)}")
            else:
                print(f"\n✗ Proxy API test failed: {result.get('msg')}")

        except Exception as e:
            print(f'Error: {e}')


async def test_multi_round_conversation():
    """测试多轮对话记忆功能 - 分轮次提取完整信息"""
    async with httpx.AsyncClient() as client:
        api_key = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
        session_id = "test_session_001"  # 固定session_id用于多轮对话

        # 定义工具 - 提取完整个人信息
        tools = [
            {
                "name": "extract_person_info",
                "description": "提取人员完整信息，包括姓名、年龄、邮箱、电话、地址",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "姓名"
                        },
                        "age": {
                            "type": "integer",
                            "description": "年龄"
                        },
                        "email": {
                            "type": "string",
                            "description": "邮箱地址"
                        },
                        "phone": {
                            "type": "string",
                            "description": "电话号码"
                        },
                        "address": {
                            "type": "string",
                            "description": "居住地址"
                        }
                    },
                    "required": ["name", "age", "email", "phone", "address"]
                }
            }
        ]

        system_prompt = "你是一个信息提取助手，请从用户输入中提取结构化信息。如果信息不完整，请提取已提供的字段。"

        print("\n" + "="*60)
        print("测试多轮对话记忆功能")
        print("="*60)

        # ========== 第一轮：提供部分信息 ==========
        print("\n【第一轮】用户提供部分信息（缺少电话和地址）")
        round1_data = {
            "query": "请提取以下信息：姓名李四，年龄30岁，邮箱lisi@example.com",
            "tools": tools,
            "system_prompt": system_prompt,
            "session_id": session_id,
            "memory_rounds": 5,
            "preferred_methods": ["with_structured_output", "custom_fc_non_stream"]
        }

        try:
            resp1 = await client.post(
                'http://localhost:9999/api/llm/proxy',
                json=round1_data,
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=60
            )
            result1 = resp1.json()

            if result1.get('code') == 200:
                data1 = result1.get('data', {})
                extracted1 = data1.get('data', {})
                print(f"✓ 第一轮调用成功")
                print(f"  使用方法: {data1.get('method')}")
                print(f"  提取结果: {json.dumps(extracted1, indent=2, ensure_ascii=False)}")

                # 检查是否缺少字段
                missing_fields = []
                if not extracted1.get('phone'):
                    missing_fields.append('电话')
                if not extracted1.get('address'):
                    missing_fields.append('地址')

                if missing_fields:
                    print(f"  ⚠ 缺少字段: {', '.join(missing_fields)}")
                else:
                    print("  ✓ 所有字段已提取")
            else:
                print(f"✗ 第一轮调用失败: {result1.get('msg')}")
                return

        except Exception as e:
            print(f'Error in round 1: {e}')
            return

        # ========== 第二轮：补充缺失信息 ==========
        print("\n【第二轮】用户补充缺失信息（电话和地址）")
        round2_data = {
            "query": "我的电话是13800138000，住在北京市朝阳区建国路88号",
            "tools": tools,
            "system_prompt": system_prompt,
            "session_id": session_id,
            "memory_rounds": 5,
            "preferred_methods": ["with_structured_output", "custom_fc_non_stream"]
        }

        try:
            resp2 = await client.post(
                'http://localhost:9999/api/llm/proxy',
                json=round2_data,
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=60
            )
            result2 = resp2.json()

            if result2.get('code') == 200:
                data2 = result2.get('data', {})
                extracted2 = data2.get('data', {})
                print(f"✓ 第二轮调用成功")
                print(f"  使用方法: {data2.get('method')}")
                print(f"  本轮提取: {json.dumps(extracted2, indent=2, ensure_ascii=False)}")

                # 验证是否提取到补充的信息
                has_phone = bool(extracted2.get('phone'))
                has_address = bool(extracted2.get('address'))

                if has_phone and has_address:
                    print("  ✓ 成功提取到电话和地址")
                else:
                    print(f"  ⚠ 仍未提取完整: 电话={has_phone}, 地址={has_address}")
            else:
                print(f"✗ 第二轮调用失败: {result2.get('msg')}")
                return

        except Exception as e:
            print(f'Error in round 2: {e}')
            return

        # ========== 第三轮：验证记忆功能（询问之前的信息） ==========
        print("\n【第三轮】验证记忆功能（询问之前提供的信息）")
        round3_data = {
            "query": "根据我之前提供的信息，我的完整信息是什么？",
            "tools": tools,
            "system_prompt": system_prompt,
            "session_id": session_id,
            "memory_rounds": 5,
            "preferred_methods": ["with_structured_output", "custom_fc_non_stream"]
        }

        try:
            resp3 = await client.post(
                'http://localhost:9999/api/llm/proxy',
                json=round3_data,
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=60
            )
            result3 = resp3.json()

            if result3.get('code') == 200:
                data3 = result3.get('data', {})
                extracted3 = data3.get('data', {})
                print(f"✓ 第三轮调用成功")
                print(f"  使用方法: {data3.get('method')}")
                print(f"  完整信息: {json.dumps(extracted3, indent=2, ensure_ascii=False)}")

                # 验证完整性
                all_fields = ['name', 'age', 'email', 'phone', 'address']
                complete = all(extracted3.get(f) for f in all_fields)

                if complete:
                    print("\n" + "="*60)
                    print("✓✓✓ 多轮对话测试通过！所有信息已完整提取")
                    print("="*60)
                    print(f"姓名: {extracted3.get('name')}")
                    print(f"年龄: {extracted3.get('age')}")
                    print(f"邮箱: {extracted3.get('email')}")
                    print(f"电话: {extracted3.get('phone')}")
                    print(f"地址: {extracted3.get('address')}")
                else:
                    print("\n⚠ 信息仍不完整")
            else:
                print(f"✗ 第三轮调用失败: {result3.get('msg')}")

        except Exception as e:
            print(f'Error in round 3: {e}')

        print("\n" + "="*60)
        print("多轮对话测试完成")
        print("="*60)


async def test_memory_rounds_limit():
    """测试记忆轮数限制（滑动窗口）"""
    async with httpx.AsyncClient() as client:
        api_key = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
        session_id = "test_session_002"

        tools = [
            {
                "name": "record_message",
                "description": "记录用户消息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "消息内容"},
                        "round_number": {"type": "integer", "description": "轮次编号"}
                    },
                    "required": ["message", "round_number"]
                }
            }
        ]

        print("\n" + "="*60)
        print("测试记忆轮数限制（设置memory_rounds=2）")
        print("="*60)

        # 进行4轮对话
        for i in range(1, 5):
            print(f"\n【第{i}轮】发送消息")

            proxy_data = {
                "query": f"这是第{i}轮的消息内容",
                "tools": tools,
                "system_prompt": "记录用户消息和轮次",
                "session_id": session_id,
                "memory_rounds": 2,  # 只保留最近2轮
                "preferred_methods": ["with_structured_output"]
            }

            try:
                resp = await client.post(
                    'http://localhost:9999/api/llm/proxy',
                    json=proxy_data,
                    headers={'Authorization': f'Bearer {api_key}'},
                    timeout=60
                )
                result = resp.json()

                if result.get('code') == 200:
                    print(f"  ✓ 第{i}轮成功")
                else:
                    print(f"  ✗ 第{i}轮失败: {result.get('msg')}")

            except Exception as e:
                print(f'  Error in round {i}: {e}')

        print("\n" + "="*60)
        print("记忆轮数限制测试完成")
        print("（由于memory_rounds=2，系统应只保留最近2轮对话）")
        print("="*60)


async def main():
    """运行所有测试"""
    print("\n" + "#"*60)
    print("# LLM Proxy 多轮对话测试脚本")
    print("#"*60)

    # 基础测试
    # await test_full_proxy()

    # 多轮对话测试
    await test_multi_round_conversation()

    # 记忆轮数限制测试
    # await test_memory_rounds_limit()

    print("\n" + "#"*60)
    print("# 所有测试完成")
    print("#"*60)


if __name__ == '__main__':
    asyncio.run(main())
