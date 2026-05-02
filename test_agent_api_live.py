"""
Query Agent 实时 API 测试
通过 Query Agent 接口查询比亚迪门店
"""
import asyncio
import sys
from typing import Dict, Any

sys.path.insert(0, '/Users/lu/code/code/py/autofill')

import httpx
from tortoise import Tortoise

from app.models.autofill import AppManagement
from app.settings.config import settings

# API 基础地址
BASE_URL = "http://localhost:9999"

# 测试场景：用户提到的具体场景
TEST_SCENARIOS = [
    {
        "name": "上海体验中心4号店",
        "chat": """用户： 我今天到你们上海体验中心店修车的时候那个服务人员态度极差
客服：好的。我帮您查一下， 是哪个店？
用户：4号店。""",
        "expected_city": "上海",
        "expected_type": "体验中心",
        "expected_number": "4号店"
    },
    {
        "name": "北京王朝网2号店",
        "chat": """用户：我想去北京王朝网看车
客服：请问是哪个店？
用户：2号店""",
        "expected_city": "北京",
        "expected_type": "王朝网",
        "expected_number": "2号店"
    },
    {
        "name": "深圳海洋网3号店",
        "chat": """客户：深圳海洋网3号店的电话是多少？
客服：请稍等，我帮您查询""",
        "expected_city": "深圳",
        "expected_type": "海洋网",
        "expected_number": "3号店"
    }
]


async def init_database():
    """初始化数据库连接"""
    await Tortoise.init(config=settings.TORTOISE_ORM)


async def get_api_key() -> str:
    """获取 API Key"""
    app = await AppManagement.filter(is_active=True).first()
    if app:
        return app.api_key
    return "test_api_key"


async def test_agent_query_api():
    """测试通过 Query Agent 接口查询"""
    print("\n" + "=" * 70)
    print("测试: 通过 Query Agent 接口查询比亚迪门店")
    print("=" * 70)

    await init_database()
    api_key = await get_api_key()
    await Tortoise.close_connections()

    print(f"\n使用 API Key: {api_key}")

    # 构建 curl 命令（指向比亚迪门店 API）
    curl_command = f"""
    curl -X POST '{BASE_URL}/api/v1/byd-dealers/public/byd-dealers/search' \
    -H 'Content-Type: application/json' \
    -d '{{
        "app_key": "{api_key}",
        "query": "{{{{keyword}}}}",
        "city": "{{{{city}}}}",
        "limit": 10
    }}'
    """

    print(f"\nCurl 命令模板:")
    print(curl_command)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:
        for i, scenario in enumerate(TEST_SCENARIOS, 1):
            print(f"\n{'='*70}")
            print(f"场景 {i}: {scenario['name']}")
            print(f"{'='*70}")
            print(f"聊天记录:\n{scenario['chat']}")

            # 构建 Agent 查询请求
            agent_request = {
                "query": scenario['chat'],
                "curl": curl_command.strip(),
                "system_prompt": """你是一个比亚迪门店查询助手。从用户的聊天记录中提取关键信息并查询门店。

任务：
1. 从聊天记录中识别城市名称（如上海、北京、深圳等）
2. 识别门店类型（如体验中心、王朝网、海洋网、4S店等）
3. 识别门店编号（如4号店、2号店、3号店等）
4. 构建搜索参数调用 API

要求：
- 返回最匹配的门店信息
- 如果找到多个匹配项，选择最相关的一个
- 返回门店的完整信息（名称、地址、电话等）""",
                "max_attempts": 3,
                "timeout": 30,
                "llm_model": "C4AI-Command-R-Plus",
                "llm_temperature": 0.0,
                "return_raw_response": True,
                "result_selector": "data.0"
            }

            try:
                print(f"\n调用 Query Agent 接口...")
                response = await client.post(
                    "/api/agent/query",
                    json=agent_request
                )

                if response.status_code == 200:
                    result = response.json()
                    print(f"✓ Agent 查询成功")
                    print(f"  - 尝试次数: {result.get('attempts', 0)}")
                    print(f"  - 是否满意: {result.get('is_satisfied', False)}")
                    print(f"  - 推理: {result.get('reasoning', '')[:100]}...")

                    data = result.get('data')
                    if data:
                        print(f"\n  ✓ 找到匹配门店:")
                        print(f"    名称: {data.get('name', 'N/A')}")
                        print(f"    城市: {data.get('city', 'N/A')}")
                        print(f"    地址: {data.get('address', 'N/A')}")
                        print(f"    电话: {data.get('phone', 'N/A')}")
                        print(f"    类型: {data.get('dealer_type', 'N/A')}")

                        # 验证是否匹配预期
                        name = data.get('name', '')
                        city = data.get('city', '')
                        if (scenario['expected_city'] in city and
                            scenario['expected_type'] in name and
                            scenario['expected_number'] in name):
                            print(f"\n  ✓✓✓ 成功匹配预期门店!")
                        else:
                            print(f"\n  ⚠ 未完全匹配预期（预期: {scenario['expected_city']}{scenario['expected_type']}{scenario['expected_number']}）")
                    else:
                        print(f"\n  ✗ 未找到匹配门店")

                    # 显示搜索历史
                    history = result.get('history', [])
                    if history:
                        print(f"\n  搜索历史:")
                        for attempt in history:
                            print(f"    尝试 {attempt.get('attempt_number')}:")
                            print(f"      参数: {attempt.get('parameters')}")
                            print(f"      结果数: {attempt.get('result_count')}")
                else:
                    print(f"✗ Agent 查询失败: {response.status_code}")
                    print(f"响应: {response.text[:500]}")

            except Exception as e:
                print(f"✗ 测试异常: {e}")
                import traceback
                traceback.print_exc()


async def test_specific_shanghai_store():
    """专门测试上海体验中心4号店"""
    print("\n" + "=" * 70)
    print("专门测试: 上海体验中心4号店")
    print("=" * 70)

    await init_database()
    api_key = await get_api_key()
    await Tortoise.close_connections()

    chat_history = """用户： 我今天到你们上海体验中心店修车的时候那个服务人员态度极差
客服：好的。我帮您查一下， 是哪个店？
用户：4号店。"""

    print(f"\n聊天记录:\n{chat_history}")
    print(f"\n预期查询: 上海 体验中心 4号店")

    # 构建 curl 命令
    curl_command = f"""
    curl -X POST '{BASE_URL}/api/v1/byd-dealers/public/byd-dealers/search' \
    -H 'Content-Type: application/json' \
    -d '{{
        "app_key": "{api_key}",
        "query": "{{{{keyword}}}}",
        "city": "{{{{city}}}}",
        "limit": 10
    }}'
    """

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:
        agent_request = {
            "query": chat_history,
            "curl": curl_command.strip(),
            "system_prompt": """从用户和客服的聊天记录中提取比亚迪门店信息。

用户提到：
- 在上海的某个体验中心店
- 具体是4号店

需要识别：
1. 城市：上海
2. 门店类型：体验中心
3. 门店编号：4号店

返回最匹配的门店完整信息。""",
            "max_attempts": 5,
            "timeout": 30,
            "llm_model": "C4AI-Command-R-Plus",
            "llm_temperature": 0.0,
            "return_raw_response": False,
            "result_selector": "data.0"
        }

        try:
            print(f"\n调用 Query Agent 接口...")
            response = await client.post(
                "/api/agent/query",
                json=agent_request
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ Agent 查询成功")
                print(f"  - 成功: {result.get('success', False)}")
                print(f"  - 尝试次数: {result.get('attempts', 0)}")
                print(f"  - 是否满意: {result.get('is_satisfied', False)}")
                print(f"  - 推理: {result.get('reasoning', '')}")

                data = result.get('data')
                if data:
                    print(f"\n✓✓✓ 找到匹配门店:")
                    print(f"  名称: {data.get('name', 'N/A')}")
                    print(f"  编码: {data.get('code', 'N/A')}")
                    print(f"  城市: {data.get('city', 'N/A')}")
                    print(f"  区县: {data.get('district', 'N/A')}")
                    print(f"  地址: {data.get('address', 'N/A')}")
                    print(f"  电话: {data.get('phone', 'N/A')}")
                    print(f"  类型: {data.get('dealer_type', 'N/A')}")
                    print(f"  状态: {data.get('status', 'N/A')}")

                    name = data.get('name', '')
                    if "上海体验中心4号店" in name or ("上海" in name and "体验中心" in name and "4号店" in name):
                        print(f"\n" + "="*70)
                        print(f"✓✓✓ 测试通过！成功找到上海体验中心4号店 ✓✓✓")
                        print(f"="*70)
                        return True
                    else:
                        print(f"\n⚠ 找到的门店不完全匹配预期")
                        return False
                else:
                    print(f"\n✗ 未找到匹配门店")
                    return False
            else:
                print(f"✗ Agent 查询失败: {response.status_code}")
                print(f"响应: {response.text[:500]}")
                return False

        except Exception as e:
            print(f"✗ 测试异常: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """主函数"""
    print("=" * 70)
    print("Query Agent 实时 API 测试")
    print("=" * 70)
    print(f"\n后端地址: {BASE_URL}")
    print("\n测试场景:")
    for i, scenario in enumerate(TEST_SCENARIOS, 1):
        print(f"  {i}. {scenario['name']}")

    results = []

    # 测试所有场景
    try:
        await test_agent_query_api()
        results.append(("Agent 查询所有场景", True))
    except Exception as e:
        print(f"\nAgent 查询测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Agent 查询所有场景", False))

    # 专门测试上海体验中心4号店
    try:
        success = await test_specific_shanghai_store()
        results.append(("上海体验中心4号店", success))
    except Exception as e:
        print(f"\n上海体验中心4号店测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("上海体验中心4号店", False))

    # 打印总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)

    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print("\n" + "=" * 70)
    print(f"测试结果: {passed_count}/{total_count} 项通过")
    if passed_count == total_count:
        print("✓ 所有测试通过！")
    else:
        print("✗ 部分测试失败")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
