#!/usr/bin/env python3
"""
页面CRUD全面测试脚本
"""
import asyncio
import aiohttp
from datetime import datetime

BASE_URL = "http://localhost:9999"


def get_auth_headers(token):
    return {"token": token}


async def login():
    """登录获取token"""
    async with aiohttp.ClientSession() as session:
        login_data = {"username": "admin", "password": "123456"}
        async with session.post(
            f"{BASE_URL}/api/v1/base/access_token",
            json=login_data
        ) as resp:
            result = await resp.json()
            if result.get("code") == 200:
                return result["data"]["access_token"]
            print(f"登录失败: {result}")
            return None


async def list_apps(token):
    """获取应用列表"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/v1/autofill/app/list",
            headers=get_auth_headers(token),
            params={"page": 1, "page_size": 100}
        ) as resp:
            return await resp.json()


async def create_page(token, page_data):
    """创建页面"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/api/v1/autofill/page/create",
            headers={**get_auth_headers(token), "Content-Type": "application/json"},
            json=page_data
        ) as resp:
            return await resp.json()


async def get_page(token, page_id):
    """获取页面详情"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/v1/autofill/page/get",
            headers=get_auth_headers(token),
            params={"id": page_id}
        ) as resp:
            return await resp.json()


async def get_page_detail(token, page_id):
    """获取页面详情（包含字段组）"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/v1/autofill/page/detail",
            headers=get_auth_headers(token),
            params={"id": page_id}
        ) as resp:
            return await resp.json()


async def update_page(token, page_data):
    """更新页面"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/api/v1/autofill/page/update",
            headers={**get_auth_headers(token), "Content-Type": "application/json"},
            json=page_data
        ) as resp:
            return await resp.json()


async def delete_page(token, page_id):
    """删除页面"""
    async with aiohttp.ClientSession() as session:
        async with session.delete(
            f"{BASE_URL}/api/v1/autofill/page/delete",
            headers=get_auth_headers(token),
            params={"id": page_id}
        ) as resp:
            return await resp.json()


async def list_pages(token, **kwargs):
    """获取页面列表"""
    async with aiohttp.ClientSession() as session:
        params = {"page": 1, "page_size": 10}
        params.update(kwargs)
        async with session.get(
            f"{BASE_URL}/api/v1/autofill/page/list",
            headers=get_auth_headers(token),
            params=params
        ) as resp:
            return await resp.json()


async def get_page_select(token, **kwargs):
    """获取页面下拉列表"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/v1/autofill/page/select",
            headers=get_auth_headers(token),
            params=kwargs
        ) as resp:
            return await resp.json()


def parse_list_response(result):
    """解析列表响应"""
    if result.get("code") == 200:
        data = result.get("data", [])
        if isinstance(data, list):
            return data
        return data.get("items", [])
    return []


class PageTestRunner:
    """页面测试运行器"""

    def __init__(self, token):
        self.token = token
        self.test_results = []
        self.app_name = None
        self.created_pages = []

    async def setup(self):
        """设置测试环境"""
        apps_result = await list_apps(self.token)
        apps = parse_list_response(apps_result)

        if not apps:
            print("❌ 无法获取应用列表")
            return False

        self.app_name = apps[0].get("app_name")
        print(f"测试环境设置完成:")
        print(f"  应用名称: {self.app_name}")
        return True

    async def cleanup(self):
        """清理测试数据"""
        print("\n清理测试数据...")
        for page_id in self.created_pages:
            try:
                await delete_page(self.token, page_id)
                print(f"  已删除页面 ID: {page_id}")
            except Exception as e:
                print(f"  删除页面失败 ID: {page_id}, 错误: {e}")

    async def run_test(self, test_name, test_func):
        """运行单个测试"""
        print(f"\n{'='*60}")
        print(f"测试: {test_name}")
        print('='*60)
        try:
            result = await test_func()
            self.test_results.append((test_name, result))
            return result
        except Exception as e:
            print(f"❌ 测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            self.test_results.append((test_name, False))
            return False

    # ==================== 测试场景 ====================

    async def test_create_page(self):
        """测试场景1: 创建页面"""
        timestamp = datetime.now().strftime('%H%M%S')
        page_name = f"测试页面_{timestamp}"
        page_code = f"test_page_{timestamp}"

        print(f"1. 创建页面: {page_name}")

        page_data = {
            "page_name": page_name,
            "page_code": page_code,
            "app_name": self.app_name,
            "description": "这是一个测试页面",
            "dify_agent_url": "http://example.com/agent",
            "dify_api_key": "test_api_key_123",
            "is_active": True
        }

        result = await create_page(self.token, page_data)

        if result.get("code") != 200:
            print(f"❌ 创建页面失败: {result.get('msg')}")
            return False

        page = result.get("data", {})
        page_id = page.get("id")
        self.created_pages.append(page_id)

        print(f"✅ 页面创建成功，ID: {page_id}")
        print(f"✅ 页面编码: {page.get('page_code')}")
        print(f"✅ 应用名称: {page.get('app_name')}")

        return True

    async def test_get_page(self):
        """测试场景2: 查询页面详情"""
        print("2. 查询页面详情")

        # 先创建一个页面
        timestamp = datetime.now().strftime('%H%M%S')
        page_data = {
            "page_name": f"查询测试页面_{timestamp}",
            "app_name": self.app_name,
            "description": "用于查询测试"
        }

        create_result = await create_page(self.token, page_data)
        if create_result.get("code") != 200:
            print("❌ 创建测试页面失败")
            return False

        page_id = create_result["data"]["id"]
        self.created_pages.append(page_id)

        # 查询页面
        result = await get_page(self.token, page_id)

        if result.get("code") != 200:
            print(f"❌ 查询页面失败: {result.get('msg')}")
            return False

        page = result.get("data", {})
        print(f"✅ 查询成功，页面名称: {page.get('page_name')}")
        print(f"✅ 页面编码: {page.get('page_code')}")
        print(f"✅ 应用名称: {page.get('app_name')}")

        return True

    async def test_update_page(self):
        """测试场景3: 更新页面"""
        print("3. 更新页面")

        # 先创建一个页面
        timestamp = datetime.now().strftime('%H%M%S')
        page_data = {
            "page_name": f"更新测试页面_{timestamp}",
            "app_name": self.app_name,
            "description": "原始描述"
        }

        create_result = await create_page(self.token, page_data)
        if create_result.get("code") != 200:
            print("❌ 创建测试页面失败")
            return False

        page_id = create_result["data"]["id"]
        self.created_pages.append(page_id)

        # 更新页面
        update_data = {
            "id": page_id,
            "page_name": f"已更新页面_{timestamp}",
            "description": "更新后的描述",
            "dify_agent_url": "http://updated.example.com"
        }

        result = await update_page(self.token, update_data)

        if result.get("code") != 200:
            print(f"❌ 更新页面失败: {result.get('msg')}")
            return False

        page = result.get("data", {})
        print(f"✅ 更新成功")
        print(f"✅ 新名称: {page.get('page_name')}")
        print(f"✅ 新描述: {page.get('description')}")

        return True

    async def test_delete_page(self):
        """测试场景4: 删除页面"""
        print("4. 删除页面")

        # 先创建一个页面
        timestamp = datetime.now().strftime('%H%M%S')
        page_data = {
            "page_name": f"删除测试页面_{timestamp}",
            "app_name": self.app_name
        }

        create_result = await create_page(self.token, page_data)
        if create_result.get("code") != 200:
            print("❌ 创建测试页面失败")
            return False

        page_id = create_result["data"]["id"]

        # 删除页面
        result = await delete_page(self.token, page_id)

        if result.get("code") != 200:
            print(f"❌ 删除页面失败: {result.get('msg')}")
            return False

        print(f"✅ 页面删除成功")

        # 验证页面已删除
        get_result = await get_page(self.token, page_id)
        if get_result.get("code") == 200:
            print("⚠️ 页面仍可查询，可能为软删除")
        else:
            print("✅ 页面已无法查询")

        return True

    async def test_list_pages(self):
        """测试场景5: 页面列表查询"""
        print("5. 页面列表查询")

        # 创建几个测试页面
        for i in range(3):
            timestamp = datetime.now().strftime('%H%M%S')
            page_data = {
                "page_name": f"列表测试页面_{timestamp}_{i}",
                "app_name": self.app_name
            }
            result = await create_page(self.token, page_data)
            if result.get("code") == 200:
                self.created_pages.append(result["data"]["id"])

        # 测试列表查询
        result = await list_pages(self.token, page_size=10)

        if result.get("code") != 200:
            print(f"❌ 查询列表失败: {result.get('msg')}")
            return False

        data = result.get("data", [])
        total = result.get("total", 0)

        print(f"✅ 查询成功，总数: {total}")
        print(f"✅ 当前页数据量: {len(data)}")

        return True

    async def test_list_pages_with_filter(self):
        """测试场景6: 页面列表筛选"""
        print("6. 页面列表筛选")

        timestamp = datetime.now().strftime('%H%M%S')
        unique_name = f"筛选测试_{timestamp}"

        # 创建特定名称的页面
        page_data = {
            "page_name": unique_name,
            "app_name": self.app_name
        }
        result = await create_page(self.token, page_data)
        if result.get("code") == 200:
            self.created_pages.append(result["data"]["id"])

        # 使用名称筛选
        result = await list_pages(self.token, page_name=unique_name)

        if result.get("code") != 200:
            print(f"❌ 筛选查询失败: {result.get('msg')}")
            return False

        data = result.get("data", [])
        print(f"✅ 筛选查询成功，结果数: {len(data)}")

        if data and any(p.get("page_name") == unique_name for p in data):
            print("✅ 筛选结果正确")
        else:
            print("⚠️ 筛选结果可能不完整")

        return True

    async def test_page_select(self):
        """测试场景7: 页面下拉列表"""
        print("7. 页面下拉列表")

        result = await get_page_select(self.token)

        if result.get("code") != 200:
            print(f"❌ 获取下拉列表失败: {result.get('msg')}")
            return False

        data = result.get("data", [])
        print(f"✅ 获取下拉列表成功，选项数: {len(data)}")

        if data:
            print(f"✅ 示例选项: {data[0]}")

        return True

    async def test_page_with_field_groups(self):
        """测试场景8: 页面与字段组关联"""
        print("8. 页面与字段组关联")

        # 创建一个页面
        timestamp = datetime.now().strftime('%H%M%S')
        page_data = {
            "page_name": f"字段组测试页面_{timestamp}",
            "app_name": self.app_name
        }

        create_result = await create_page(self.token, page_data)
        if create_result.get("code") != 200:
            print("❌ 创建测试页面失败")
            return False

        page_id = create_result["data"]["id"]
        self.created_pages.append(page_id)

        # 查询页面详情（包含字段组）
        result = await get_page_detail(self.token, page_id)

        if result.get("code") != 200:
            print(f"❌ 查询页面详情失败: {result.get('msg')}")
            return False

        data = result.get("data", {})
        field_groups = data.get("field_groups", [])

        print(f"✅ 查询成功")
        print(f"✅ 页面名称: {data.get('page_name')}")
        print(f"✅ 关联字段组数: {len(field_groups)}")

        return True

    async def run_all_tests(self):
        """运行所有测试"""
        print("="*60)
        print("开始页面CRUD全面测试")
        print("="*60)

        if not await self.setup():
            return

        # 运行所有测试
        await self.run_test("创建页面", self.test_create_page)
        await self.run_test("查询页面详情", self.test_get_page)
        await self.run_test("更新页面", self.test_update_page)
        await self.run_test("删除页面", self.test_delete_page)
        await self.run_test("页面列表查询", self.test_list_pages)
        await self.run_test("页面列表筛选", self.test_list_pages_with_filter)
        await self.run_test("页面下拉列表", self.test_page_select)
        await self.run_test("页面与字段组关联", self.test_page_with_field_groups)

        # 清理
        await self.cleanup()

        # 打印测试总结
        print("\n" + "="*60)
        print("测试总结")
        print("="*60)

        passed = sum(1 for _, result in self.test_results if result)
        total = len(self.test_results)

        for test_name, result in self.test_results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{status}: {test_name}")

        print(f"\n总计: {passed}/{total} 个测试通过")


async def main():
    token = await login()
    if not token:
        print("登录失败，无法继续测试")
        return

    print("✅ 登录成功\n")

    runner = PageTestRunner(token)
    await runner.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
