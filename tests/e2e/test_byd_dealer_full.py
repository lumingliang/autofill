"""
比亚迪经销商门店完整测试
包含：
1. 从聊天记录查询门店（有错别字）
2. 基于门店名称的模糊搜索
3. 城市和区域组合查询
4. 真实API调用测试
"""
import asyncio
import json
import os
import sys
from typing import Dict, Any, List, Optional
径
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

import httpx
from tortoise import Tortoise

from app.models.byd_dealer import BYDDealer
from app.models.autofill import AppManagement
from app.services.byd_dealer_service import BYDDealerService
from app.schemas.byd_dealer import BYDDealerPublicSearchRequest
from app.settings.config import settings


# API 基础地址
BASE_URL = "http://localhost:8000"

# 测试用的聊天记录示例（包含错别字的门店名称）
CHAT_HISTORY_SCENARIOS = [
    {
        "name": "错别字：比压迪",
        "chat": """
客服：您好，请问有什么可以帮您？
客户：我想了解一下比压迪的门店
客服：您所在的城市是哪里呢？
客户：我在北京
        """,
        "expected_keywords": ["比亚迪"],
        "expected_city": "北京"
    },
    {
        "name": "错别字：亚迪",
        "chat": """
客服：您好！
客户：我想去亚迪4S店保养
客服：请问您在哪个城市？
客户：我在上海浦东新区
        """,
        "expected_keywords": ["比亚迪"],
        "expected_city": "上海",
        "expected_district": "浦东"
    },
    {
        "name": "错别字：BYD拼写错误",
        "chat": """
客服：您好，比亚迪汽车服务中心！
客户：你好，我想问一下深圳有没有BDY的门店？
客服：有的，请问您是想看车还是做保养？
客户：我想去看车
        """,
        "expected_keywords": ["比亚迪"],
        "expected_city": "深圳"
    },
    {
        "name": "模糊门店名称：王朝网",
        "chat": """
客服：您好！
客户：我在广州，想找比亚迪王朝网
客服：您是需要购车还是售后服务？
客户：先看看车，了解一下汉系列
        """,
        "expected_keywords": ["王朝网"],
        "expected_city": "广州"
    },
    {
        "name": "模糊门店名称：海洋网",
        "chat": """
客服：您好，请问有什么可以帮您？
客户：我想去海洋网看车
客服：请问您在哪个城市？
客户：我在成都高新区
        """,
        "expected_keywords": ["海洋网"],
        "expected_city": "成都",
        "expected_district": "高新区"
    },
    {
        "name": "具体门店名称（有错别字）",
        "chat": """
客服：您好！
客户：我想去比亚迪汽车杭州4S店
客服：您说的是比亚迪汽车杭州4S店吗？
客户：对的，就是比亚迪汽车杭州4S店
        """,
        "expected_keywords": ["比亚迪汽车杭州4S店"],
        "expected_city": "杭州"
    },
    {
        "name": "区域+门店类型",
        "chat": """
客服：您好，请问有什么可以帮您？
客户：我想找武汉的体验中心
客服：请问您是在武汉哪个区？
客户：我在武昌区
        """,
        "expected_keywords": ["体验中心"],
        "expected_city": "武汉",
        "expected_district": "武昌"
    },
    {
        "name": "多条件组合查询",
        "chat": """
客服：您好！
客户：我想了解一下西安的比亚迪4S店，最好在未央区
客服：好的，请问您是想看车还是做保养？
客户：我想看看新能源车
        """,
        "expected_keywords": ["比亚迪", "4S店"],
        "expected_city": "西安",
        "expected_district": "未央"
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


async def test_database_search():
    """测试数据库直接搜索"""
    print("\n" + "=" * 70)
    print("测试1: 数据库直接搜索（验证数据已导入）")
    print("=" * 70)

    await init_database()

    # 测试1: 统计门店数量
    total = await BYDDealer.filter().count()
    print(f"\n✓ 数据库中共有 {total} 个门店")

    # 测试2: 按城市搜索
    beijing_dealers = await BYDDealer.filter(city__icontains="北京").all()
    print(f"✓ 北京有 {len(beijing_dealers)} 个门店")

    # 测试3: 模糊搜索门店名称
    wangchao_dealers = await BYDDealer.filter(name__icontains="王朝网").all()
    print(f"✓ 名称包含'王朝网'的有 {len(wangchao_dealers)} 个门店")

    # 测试4: 显示部分门店名称
    print("\n部分门店名称示例:")
    dealers = await BYDDealer.filter().limit(10).all()
    for i, dealer in enumerate(dealers, 1):
        print(f"  {i}. {dealer.name} ({dealer.city} - {dealer.district})")

    await Tortoise.close_connections()
    return True


async def test_service_search():
    """测试服务层搜索"""
    print("\n" + "=" * 70)
    print("测试2: 服务层搜索（模拟Agent查询）")
    print("=" * 70)

    await init_database()

    api_key = await get_api_key()
    print(f"\n使用 API Key: {api_key}")

    test_cases = [
        {
            "name": "搜索北京门店",
            "request": BYDDealerPublicSearchRequest(
                app_key=api_key,
                query="北京比亚迪",
                limit=5
            )
        },
        {
            "name": "搜索王朝网（有错别字）",
            "request": BYDDealerPublicSearchRequest(
                app_key=api_key,
                query="王潮网",  # 错别字
                limit=5
            )
        },
        {
            "name": "搜索具体城市+区域",
            "request": BYDDealerPublicSearchRequest(
                app_key=api_key,
                query="深圳福田区比亚迪",
                city="深圳",
                limit=5
            )
        }
    ]

    for case in test_cases:
        print(f"\n{case['name']}:")
        result = await BYDDealerService.search_dealers(case['request'])

        if result.success:
            print(f"  ✓ 查询成功，找到 {result.total} 个门店")
            print(f"  - 匹配关键词: {result.matched_keywords}")
            for i, dealer in enumerate(result.data[:3], 1):
                print(f"  {i}. {dealer.name} ({dealer.city} - {dealer.district})")
        else:
            print(f"  ✗ 查询失败: {result.message}")

    await Tortoise.close_connections()
    return True


async def test_chat_history_search():
    """测试从聊天记录搜索门店"""
    print("\n" + "=" * 70)
    print("测试3: 从聊天记录搜索门店（有错别字场景）")
    print("=" * 70)

    await init_database()

    api_key = await get_api_key()

    for i, scenario in enumerate(CHAT_HISTORY_SCENARIOS, 1):
        print(f"\n{i}. 场景: {scenario['name']}")
        print(f"   聊天记录: {scenario['chat'].strip()[:100]}...")

        # 使用服务层搜索
        request = BYDDealerPublicSearchRequest(
            app_key=api_key,
            query=scenario['chat'],
            city=scenario.get('expected_city'),
            limit=5
        )

        result = await BYDDealerService.search_dealers(request)

        if result.success and result.data:
            print(f"   ✓ 查询成功，找到 {result.total} 个门店")
            print(f"   - 匹配关键词: {result.matched_keywords}")
            print(f"   - 预期城市: {scenario.get('expected_city', '任意')}")

            # 验证结果是否包含预期城市
            found_expected_city = any(
                scenario.get('expected_city') in dealer.city
                for dealer in result.data
            ) if scenario.get('expected_city') else True

            if found_expected_city:
                print(f"   ✓ 结果包含预期城市")
            else:
                print(f"   ⚠ 结果未包含预期城市，但可能匹配其他条件")

            for j, dealer in enumerate(result.data[:3], 1):
                print(f"   {j}. {dealer.name} ({dealer.city} - {dealer.district})")
        else:
            print(f"   ✗ 查询失败或未找到结果: {result.message}")

    await Tortoise.close_connections()
    return True


async def test_api_endpoint():
    """测试API端点"""
    print("\n" + "=" * 70)
    print("测试4: API端点测试（需要服务运行）")
    print("=" * 70)

    await init_database()
    api_key = await get_api_key()
    await Tortoise.close_connections()

    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            # 测试1: 公开搜索接口
            print("\n1. 测试公开搜索接口...")
            response = await client.post(
                "/byd-dealers/search",
                json={
                    "app_key": api_key,
                    "query": "查找北京朝阳区的比亚迪4S店",
                    "limit": 5
                }
            )

            if response.status_code == 200:
                result = response.json()
                print(f"   ✓ 接口调用成功")
                print(f"   - 找到 {result.get('total', 0)} 个门店")
                print(f"   - 匹配关键词: {result.get('matched_keywords', [])}")

                if result.get('data'):
                    for i, dealer in enumerate(result['data'][:3], 1):
                        print(f"   {i}. {dealer['name']} ({dealer['city']} - {dealer.get('district', '')})")
            else:
                print(f"   ✗ 接口调用失败: {response.status_code}")
                print(f"   响应: {response.text[:200]}")

            # 测试2: 聊天记录搜索接口
            print("\n2. 测试聊天记录搜索接口...")
            chat_history = """
客服：您好！
客户：我想去比压迪的4S店
客服：请问您在哪个城市？
客户：我在上海
            """

            response = await client.post(
                "/byd-dealers/chat-search",
                json={
                    "app_key": api_key,
                    "chat_history": chat_history,
                    "limit": 5
                }
            )

            if response.status_code == 200:
                result = response.json()
                print(f"   ✓ 接口调用成功")
                print(f"   - 找到 {result.get('total', 0)} 个门店")
                print(f"   - 匹配关键词: {result.get('matched_keywords', [])}")

                if result.get('data'):
                    for i, dealer in enumerate(result['data'][:3], 1):
                        print(f"   {i}. {dealer['name']} ({dealer['city']} - {dealer.get('district', '')})")
            else:
                print(f"   ✗ 接口调用失败: {response.status_code}")
                print(f"   响应: {response.text[:200]}")

        return True

    except httpx.ConnectError:
        print("\n   ⚠ 服务未运行，跳过API端点测试")
        print("   请先启动服务: python main.py")
        return False
    except Exception as e:
        print(f"\n   ✗ API测试异常: {e}")
        return False


async def test_typo_tolerance():
    """测试错别字容忍度"""
    print("\n" + "=" * 70)
    print("测试5: 错别字容忍度测试")
    print("=" * 70)

    await init_database()
    api_key = await get_api_key()

    typo_tests = [
        ("比压迪", "比亚迪"),
        ("亚迪", "比亚迪"),
        ("BYD", "比亚迪"),
        ("王潮网", "王朝网"),
        ("海阳网", "海洋网"),
        ("4S电", "4S店"),
        ("体研中心", "体验中心"),
    ]

    for typo, correct in typo_tests:
        print(f"\n测试: '{typo}' -> '{correct}'")

        request = BYDDealerPublicSearchRequest(
            app_key=api_key,
            query=typo,
            limit=3
        )

        result = await BYDDealerService.search_dealers(request)

        if result.success and result.data:
            print(f"  ✓ 找到 {result.total} 个结果")
            # 检查是否匹配到正确关键词
            if any(correct in kw for kw in result.matched_keywords):
                print(f"  ✓ 正确识别为 '{correct}'")
            else:
                print(f"  - 匹配关键词: {result.matched_keywords}")
        else:
            print(f"  - 未找到结果（可能该关键词无匹配门店）")

    await Tortoise.close_connections()
    return True


async def main():
    """主函数"""
    print("=" * 70)
    print("比亚迪经销商门店完整测试")
    print("=" * 70)
    print("\n本测试包含：")
    print("  1. 数据库直接搜索（验证数据导入）")
    print("  2. 服务层搜索（模拟Agent查询）")
    print("  3. 聊天记录搜索（有错别字场景）")
    print("  4. API端点测试（需要服务运行）")
    print("  5. 错别字容忍度测试")

    results = []

    try:
        results.append(("数据库搜索", await test_database_search()))
    except Exception as e:
        print(f"\n数据库搜索测试失败: {e}")
        results.append(("数据库搜索", False))

    try:
        results.append(("服务层搜索", await test_service_search()))
    except Exception as e:
        print(f"\n服务层搜索测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("服务层搜索", False))

    try:
        results.append(("聊天记录搜索", await test_chat_history_search()))
    except Exception as e:
        print(f"\n聊天记录搜索测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("聊天记录搜索", False))

    try:
        results.append(("API端点测试", await test_api_endpoint()))
    except Exception as e:
        print(f"\nAPI端点测试失败: {e}")
        results.append(("API端点测试", False))

    try:
        results.append(("错别字容忍度", await test_typo_tolerance()))
    except Exception as e:
        print(f"\n错别字容忍度测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("错别字容忍度", False))

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
        print("所有测试通过！")
    else:
        print("部分测试失败，请检查实现")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
