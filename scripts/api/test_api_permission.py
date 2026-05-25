#!/usr/bin/env python3
"""
API权限与角色权限系统自动化测试脚本
"""
import asyncio
import httpx
from typing import List, Dict, Any

# 测试配置
BASE_URL = "http://localhost:3200"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "123456"

class PermissionTester:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        self.admin_token = None
        self.test_results = []
        
    async def login(self, username: str, password: str) -> str:
        """登录获取token"""
        resp = await self.client.post("/api/v1/base/access_token", json={
            "username": username,
            "password": password
        })
        data = resp.json()
        if data["code"] == 200:
            return data["data"]["access_token"]
        raise Exception(f"登录失败: {data}")
    
    async def admin_login(self):
        """管理员登录"""
        self.admin_token = await self.login(ADMIN_USERNAME, ADMIN_PASSWORD)
        print(f"✓ 管理员登录成功")
        
    async def create_tenant(self, name: str, domain: str, description: str) -> int:
        """创建租户"""
        resp = await self.client.post("/api/v1/tenant/create", 
            headers={"token": self.admin_token},
            json={"name": name, "domain": domain, "description": description}
        )
        data = resp.json()
        if data["code"] == 200:
            tenant_id = data["data"]["id"]
            print(f"✓ 创建租户成功: {name} (id={tenant_id})")
            return tenant_id
        # 如果已存在，查询获取id
        resp = await self.client.get("/api/v1/tenant/list",
            headers={"token": self.admin_token},
            params={"name": name, "page": 1, "page_size": 10}
        )
        data = resp.json()
        if data["code"] == 200 and data["data"]:
            for item in data["data"]:
                if item["name"] == name:
                    tenant_id = item["id"]
                    print(f"✓ 租户已存在: {name} (id={tenant_id})")
                    return tenant_id
        raise Exception(f"创建租户失败: {data}")
    
    async def create_role(self, tenant_id: int, role_name: str, description: str) -> int:
        """创建角色"""
        resp = await self.client.post("/api/v1/role/create",
            headers={"token": self.admin_token},
            json={"name": role_name, "tenant_id": tenant_id, "description": description}
        )
        data = resp.json()
        if data["code"] == 200 and data.get("data"):
            role_id = data["data"]["id"]
            print(f"✓ 创建角色成功: {role_name} (id={role_id})")
            return role_id
        # 如果已存在，查询获取id
        resp = await self.client.get("/api/v1/role/list",
            headers={"token": self.admin_token},
            params={"tenant_id": tenant_id, "page": 1, "page_size": 100}
        )
        data = resp.json()
        if data["code"] == 200 and data.get("data"):
            items = data["data"] if isinstance(data["data"], list) else data["data"].get("items", [])
            for item in items:
                if item.get("name") == role_name and item.get("tenant_id") == tenant_id:
                    role_id = item["id"]
                    print(f"✓ 角色已存在: {role_name} (id={role_id})")
                    return role_id
        raise Exception(f"创建角色失败: {data}")
    
    async def set_role_apis(self, role_id: int, api_codes: List[str]):
        """设置角色API权限"""
        # 先获取角色当前权限
        resp = await self.client.get(f"/api/v1/role/authorized",
            headers={"token": self.admin_token},
            params={"id": role_id}
        )
        data = resp.json()
        if data["code"] != 200:
            raise Exception(f"获取角色权限失败: {data}")
        
        current = data["data"]
        menu_ids = current.get("menu_ids", [])
        
        # 设置新的API权限
        resp = await self.client.post("/api/v1/role/authorized",
            headers={"token": self.admin_token},
            json={"id": role_id, "menu_ids": menu_ids, "api_codes": api_codes}
        )
        data = resp.json()
        if data["code"] == 200:
            print(f"✓ 设置角色API权限成功: {api_codes}")
        else:
            raise Exception(f"设置角色API权限失败: {data}")
    
    async def set_role_menus(self, role_id: int, menu_ids: List[int]):
        """设置角色菜单权限"""
        resp = await self.client.get(f"/api/v1/role/authorized",
            headers={"token": self.admin_token},
            params={"id": role_id}
        )
        data = resp.json()
        if data["code"] != 200:
            raise Exception(f"获取角色权限失败: {data}")
        
        current = data["data"]
        api_codes = current.get("api_codes", [])
        
        resp = await self.client.post("/api/v1/role/authorized",
            headers={"token": self.admin_token},
            json={"id": role_id, "menu_ids": menu_ids, "api_codes": api_codes}
        )
        data = resp.json()
        if data["code"] == 200:
            print(f"✓ 设置角色菜单权限成功: {menu_ids}")
        else:
            raise Exception(f"设置角色菜单权限失败: {data}")
    
    async def create_user(self, tenant_id: int, username: str, email: str, password: str, role_ids: List[int]) -> int:
        """创建用户"""
        resp = await self.client.post("/api/v1/user/create",
            headers={"token": self.admin_token},
            json={
                "username": username,
                "email": email,
                "password": password,
                "tenant_id": tenant_id,
                "role_ids": role_ids,
                "is_superuser": False
            }
        )
        data = resp.json()
        # 创建成功，但可能没有返回data，需要查询获取id
        if data["code"] == 200:
            if data.get("data") and data["data"].get("id"):
                user_id = data["data"]["id"]
                print(f"✓ 创建用户成功: {username} (id={user_id})")
                return user_id
            # 查询获取id
            resp = await self.client.get("/api/v1/user/list",
                headers={"token": self.admin_token},
                params={"page": 1, "page_size": 100}
            )
            list_data = resp.json()
            if list_data["code"] == 200 and list_data.get("data"):
                items = list_data["data"] if isinstance(list_data["data"], list) else list_data["data"].get("items", [])
                for item in items:
                    if item.get("username") == username:
                        user_id = item["id"]
                        print(f"✓ 创建/找到用户: {username} (id={user_id})")
                        return user_id
        # 如果已存在(邮箱或用户名重复)，查询获取id
        if data["code"] == 400 and ("已被注册" in data.get("msg", "") or "已存在" in data.get("msg", "")):
            resp = await self.client.get("/api/v1/user/list",
                headers={"token": self.admin_token},
                params={"page": 1, "page_size": 100}
            )
            data = resp.json()
            if data["code"] == 200 and data.get("data"):
                items = data["data"] if isinstance(data["data"], list) else data["data"].get("items", [])
                for item in items:
                    if item.get("username") == username:
                        user_id = item["id"]
                        print(f"✓ 用户已存在: {username} (id={user_id})")
                        return user_id
        raise Exception(f"创建用户失败: {data}")
    
    async def test_api_access(self, token: str, method: str, path: str, expected_status: int, description: str) -> bool:
        """测试API访问权限"""
        try:
            if method == "GET":
                resp = await self.client.get(path, headers={"token": token})
            elif method == "POST":
                resp = await self.client.post(path, headers={"token": token}, json={})
            elif method == "PUT":
                resp = await self.client.put(path, headers={"token": token}, json={})
            elif method == "DELETE":
                resp = await self.client.delete(path, headers={"token": token})
            else:
                raise Exception(f"不支持的HTTP方法: {method}")
            
            actual_status = resp.status_code
            success = actual_status == expected_status
            
            result = {
                "description": description,
                "method": method,
                "path": path,
                "expected": expected_status,
                "actual": actual_status,
                "success": success
            }
            self.test_results.append(result)
            
            status_icon = "✓" if success else "✗"
            print(f"{status_icon} {description}: {method} {path} - 期望{expected_status}, 实际{actual_status}")
            return success
        except Exception as e:
            result = {
                "description": description,
                "method": method,
                "path": path,
                "expected": expected_status,
                "actual": str(e),
                "success": False
            }
            self.test_results.append(result)
            print(f"✗ {description}: {method} {path} - 异常: {e}")
            return False
    
    async def run_scene1(self):
        """执行场景1: 单租户单角色单用户基础权限"""
        print("\n" + "="*60)
        print("场景1: 单租户单角色单用户基础权限")
        print("="*60)
        
        # 1. 创建租户A
        tenant_a_id = await self.create_tenant("测试租户A", "tenant-a", "场景1测试租户")
        
        # 2. 创建角色R1(只有user:list权限)
        role_r1_id = await self.create_role(tenant_a_id, "R1_用户查看员", "只能查看用户列表")
        await self.set_role_apis(role_r1_id, ["user:list"])
        
        # 3. 创建用户U1并分配角色R1
        import time
        timestamp = int(time.time()) % 10000  # 只取后4位，缩短用户名
        user_u1_id = await self.create_user(
            tenant_a_id, f"u1_{timestamp}", f"u1_{timestamp}@t.com", "Test123456", [role_r1_id]
        )
        
        # 4. 用户U1登录
        u1_token = await self.login("scene1_user", "Test123456")
        print(f"✓ 用户U1登录成功")
        
        # 5. 测试各种API访问
        print("\n开始测试API权限:")
        
        # 5.1 应该成功的权限
        await self.test_api_access(u1_token, "GET", "/api/v1/user/list?page=1&page_size=10", 200, "查看用户列表")
        
        # 5.2 应该失败的权限
        await self.test_api_access(u1_token, "GET", "/api/v1/dept/list", 403, "查看部门列表(无权限)")
        await self.test_api_access(u1_token, "POST", "/api/v1/user/create", 403, "创建用户(无权限)")
        await self.test_api_access(u1_token, "DELETE", "/api/v1/user/delete/1", 403, "删除用户(无权限)")
        await self.test_api_access(u1_token, "PUT", "/api/v1/user/update/1", 403, "更新用户(无权限)")
        await self.test_api_access(u1_token, "GET", "/api/v1/role/list", 403, "查看角色列表(无权限)")
        
        print(f"\n场景1测试完成")
    
    async def run_scene2(self):
        """执行场景2: 单租户多角色权限叠加"""
        print("\n" + "="*60)
        print("场景2: 单租户多角色权限叠加")
        print("="*60)
        
        # 获取租户A
        tenant_a_id = 1  # 使用已知的租户A ID
        
        # 1. 创建角色R2(有dept:list权限)
        role_r2_id = await self.create_role(tenant_a_id, "R2_部门查看员", "只能查看部门列表")
        await self.set_role_apis(role_r2_id, ["dept:list"])
        
        # 2. 获取R1角色ID
        resp = await self.client.get("/api/v1/role/list",
            headers={"token": self.admin_token},
            params={"tenant_id": tenant_a_id, "page": 1, "page_size": 100}
        )
        data = resp.json()
        role_r1_id = None
        if data["code"] == 200 and data.get("data"):
            items = data["data"] if isinstance(data["data"], list) else data["data"].get("items", [])
            for item in items:
                if item.get("name") == "R1_用户查看员":
                    role_r1_id = item["id"]
                    break
        
        if not role_r1_id:
            raise Exception("未找到R1角色")
        
        # 3. 创建用户U2，同时分配R1和R2
        import time
        timestamp = int(time.time()) % 10000
        user_u2_id = await self.create_user(
            tenant_a_id, f"u2_{timestamp}", f"u2_{timestamp}@t.com", "Test123456", [role_r1_id, role_r2_id]
        )
        
        # 4. 用户U2登录
        u2_token = await self.login(f"u2_{timestamp}", "Test123456")
        print(f"✓ 用户U2登录成功")
        
        # 5. 测试权限叠加
        print("\n开始测试权限叠加:")
        await self.test_api_access(u2_token, "GET", "/api/v1/user/list?page=1&page_size=10", 200, "查看用户列表(R1权限)")
        await self.test_api_access(u2_token, "GET", "/api/v1/dept/list", 200, "查看部门列表(R2权限)")
        await self.test_api_access(u2_token, "GET", "/api/v1/role/list", 403, "查看角色列表(无权限)")
        await self.test_api_access(u2_token, "POST", "/api/v1/dept/create", 403, "创建部门(无权限)")
        
        print(f"\n场景2测试完成")
    
    async def run_scene3(self):
        """执行场景3: 多租户权限隔离"""
        print("\n" + "="*60)
        print("场景3: 多租户权限隔离")
        print("="*60)
        
        # 1. 创建租户B
        tenant_b_id = await self.create_tenant("测试租户B", "tenant-b", "场景3测试租户")
        
        # 2. 在租户B创建角色R3(有user:list权限)
        role_r3_id = await self.create_role(tenant_b_id, "R3_用户查看员", "租户B的用户查看员")
        await self.set_role_apis(role_r3_id, ["user:list"])
        
        # 3. 在租户B创建用户U3
        user_u3_id = await self.create_user(
            tenant_b_id, "scene3_user", "scene3@test.com", "Test123456", [role_r3_id]
        )
        
        # 4. 用户U3登录
        u3_token = await self.login("scene3_user", "Test123456")
        print(f"✓ 用户U3登录成功(租户B)")
        
        # 5. 测试多租户隔离
        print("\n开始测试多租户隔离:")
        
        # U3应该能访问租户B的用户列表
        await self.test_api_access(u3_token, "GET", "/api/v1/user/list?page=1&page_size=10", 200, "U3访问租户B用户列表")
        
        # U3不应该看到租户A的用户数据(应该返回空或403)
        # 注意：这里取决于后端实现，可能是200但数据为空，也可能是403
        resp = await self.client.get("/api/v1/user/list?page=1&page_size=10", 
            headers={"Authorization": f"Bearer {u3_token}"}
        )
        data = resp.json()
        if data["code"] == 200:
            items = data["data"].get("items", [])
            # 检查是否只包含租户B的用户
            has_other_tenant = any("scene1" in str(item) or "scene2" in str(item) for item in items)
            if not has_other_tenant:
                print(f"✓ U3只能看到租户B的用户数据(隔离正常)")
            else:
                print(f"✗ U3看到了其他租户的用户数据(隔离失败!)")
        
        print(f"\n场景3测试完成")
    
    async def print_report(self):
        """打印测试报告"""
        print("\n" + "="*60)
        print("测试报告")
        print("="*60)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["success"])
        failed = total - passed
        
        print(f"\n总计: {total} 项测试")
        print(f"通过: {passed} 项")
        print(f"失败: {failed} 项")
        print(f"通过率: {passed/total*100:.1f}%" if total > 0 else "N/A")
        
        if failed > 0:
            print("\n失败的测试项:")
            for r in self.test_results:
                if not r["success"]:
                    print(f"  - {r['description']}: 期望{r['expected']}, 实际{r['actual']}")
    
    async def run_all_tests(self):
        """执行所有测试场景"""
        try:
            await self.admin_login()
            await self.run_scene1()
            await self.run_scene2()
            await self.run_scene3()
            await self.print_report()
        except Exception as e:
            print(f"\n测试执行出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.client.aclose()

async def main():
    tester = PermissionTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
