#!/usr/bin/env python3
"""
智能填单系统 - 完整功能测试

测试范围：
1. 后端管理功能（应用、页面、字段组、字段）
2. Public填单功能（字段组查询、LLM填单、AI填单）

使用方法:
    python tests/full_system_test.py

环境变量:
    BASE_URL: 后端服务地址 (默认: http://127.0.0.1:9999)
    ADMIN_USERNAME: 管理员用户名 (默认: admin)
    ADMIN_PASSWORD: 管理员密码 (默认: 123456)
    APP_NAME: 应用名称 (默认: test_app_full)
    API_KEY: API Key (可选，如果不提供则使用已有应用或创建新应用)
"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx


# 测试配置
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:9999")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "123456")
APP_NAME = os.getenv("APP_NAME", "test_app_full")
API_KEY = os.getenv("API_KEY", "")


@dataclass
class TestContext:
    """测试上下文"""
    tenant_id: int = 1
    admin_token: Optional[str] = None
    api_key: Optional[str] = None
    use_existing_app: bool = False
    
    # 创建的资源ID
    app_id: Optional[int] = None
    app_name: str = APP_NAME
    page_id: Optional[int] = None
    page_name: str = ""
    field_group_id: Optional[int] = None
    field_group_name: str = ""
    
    # 字段ID列表
    field_ids: List[int] = field(default_factory=list)
    
    # 字段名前缀（用于避免重复）
    field_prefix: str = ""


class FullSystemTester:
    """完整系统测试器"""
    
    def __init__(self):
        self.context = TestContext()
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results: List[Dict] = []
        # 生成唯一的页面和字段组名称
        timestamp = datetime.now().strftime("%m%d%H%M%S")
        self.context.page_name = f"test_page_{timestamp}"
        self.context.field_group_name = f"test_group_{timestamp}"
        self.context.field_prefix = f"test_{timestamp}_"
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
        await self.client.aclose()
        
    def log(self, message: str, level: str = "info"):
        """打印日志"""
        prefix = {"info": "ℹ️", "success": "✅", "error": "❌", "warning": "⚠️"}.get(level, "ℹ️")
        print(f"{prefix} {message}")
        
    def record_result(self, test_name: str, success: bool, details: str = "", error: str = ""):
        """记录测试结果"""
        self.test_results.append({
            "name": test_name,
            "success": success,
            "details": details,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        
    async def admin_login(self) -> bool:
        """管理员登录获取token"""
        try:
            resp = await self.client.post(
                f"{BASE_URL}/api/v1/base/access_token",
                json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
            )
            data = resp.json()
            if data.get("code") == 200:
                self.context.admin_token = data["data"]["access_token"]
                self.log("管理员登录成功", "success")
                return True
            else:
                self.log(f"登录失败: {data.get('msg')}", "error")
                return False
        except Exception as e:
            self.log(f"登录异常: {e}", "error")
            return False
    
    def admin_headers(self) -> Dict[str, str]:
        """获取管理员请求头"""
        return {
            "Content-Type": "application/json",
            "token": self.context.admin_token or ""
        }
    
    def public_headers(self) -> Dict[str, str]:
        """获取Public API请求头"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.context.api_key or ''}"
        }
    
    async def get_or_create_app(self) -> bool:
        """获取或创建应用"""
        # 如果环境变量提供了API Key，直接使用
        if API_KEY:
            self.context.api_key = API_KEY
            self.log(f"使用环境变量提供的API Key", "info")
        
        # 先尝试查询已有应用
        try:
            resp = await self.client.get(
                f"{BASE_URL}/api/v1/autofill/app/list",
                headers=self.admin_headers(),
                params={"app_name": self.context.app_name, "page": 1, "page_size": 10}
            )
            data = resp.json()
            if data.get("code") == 200:
                app_list = data['data'].get('list', []) if isinstance(data['data'], dict) else data['data']
                for app in app_list:
                    if app.get('app_name') == self.context.app_name:
                        self.context.app_id = app.get('id')
                        self.context.api_key = app.get('api_key')
                        self.context.use_existing_app = True
                        self.log(f"使用已有应用: ID={self.context.app_id}, API Key={self.context.api_key}", "success")
                        self.record_result("获取已有应用", True, f"ID={self.context.app_id}")
                        return True
        except Exception as e:
            self.log(f"查询应用异常: {e}", "warning")
        
        # 没有已有应用，尝试创建
        self.log(f"未找到已有应用，尝试创建新应用...", "info")
        try:
            resp = await self.client.post(
                f"{BASE_URL}/api/v1/autofill/app/create",
                headers=self.admin_headers(),
                json={
                    "app_name": self.context.app_name,
                    "description": "完整功能测试应用",
                    "is_active": True
                }
            )
            data = resp.json()
            if data.get("code") == 200:
                self.context.app_id = data["data"]["id"]
                self.context.api_key = data["data"]["api_key"]
                self.log(f"创建应用成功: ID={self.context.app_id}, API Key={self.context.api_key}", "success")
                self.record_result("创建应用", True, f"ID={self.context.app_id}")
                return True
            else:
                self.log(f"创建应用失败: {data.get('msg')}", "error")
                self.record_result("创建应用", False, error=data.get('msg'))
                return False
        except Exception as e:
            self.log(f"创建应用异常: {e}", "error")
            self.record_result("创建应用", False, error=str(e))
            return False
    
    # ==================== 第一阶段：后端管理功能测试 ====================
    
    async def test_app_management(self) -> bool:
        """测试应用管理功能"""
        self.log("\n========== 测试应用管理 ==========")
        success = True
        
        # 获取或创建应用
        if not await self.get_or_create_app():
            return False
        
        # 获取应用列表
        try:
            resp = await self.client.get(
                f"{BASE_URL}/api/v1/autofill/app/list",
                headers=self.admin_headers(),
                params={"page": 1, "page_size": 10}
            )
            data = resp.json()
            if data.get("code") == 200:
                total = data['data'].get('total', 0) if isinstance(data['data'], dict) else len(data['data'])
                self.log(f"获取应用列表成功: 共{total}条", "success")
                self.record_result("获取应用列表", True)
            else:
                self.log(f"获取应用列表失败: {data.get('msg')}", "error")
                self.record_result("获取应用列表", False, error=data.get('msg'))
                success = False
        except Exception as e:
            self.log(f"获取应用列表异常: {e}", "error")
            self.record_result("获取应用列表", False, error=str(e))
            success = False
        
        return success
    
    async def test_page_management(self) -> bool:
        """测试填单页面管理功能"""
        self.log("\n========== 测试填单页面管理 ==========")
        success = True
        
        # 1. 创建页面（使用app_name）
        try:
            resp = await self.client.post(
                f"{BASE_URL}/api/v1/autofill/page/create",
                headers=self.admin_headers(),
                json={
                    "page_name": self.context.page_name,
                    "page_code": self.context.page_name,
                    "app_name": self.context.app_name,
                    "description": "完整功能测试页面",
                    "is_active": True
                }
            )
            data = resp.json()
            if data.get("code") == 200:
                self.context.page_id = data["data"]["id"]
                self.log(f"创建页面成功: ID={self.context.page_id}", "success")
                self.record_result("创建页面", True, f"ID={self.context.page_id}")
            else:
                self.log(f"创建页面失败: {data.get('msg')}", "error")
                self.record_result("创建页面", False, error=data.get('msg'))
                success = False
        except Exception as e:
            self.log(f"创建页面异常: {e}", "error")
            self.record_result("创建页面", False, error=str(e))
            success = False
        
        # 2. 获取页面列表
        try:
            resp = await self.client.get(
                f"{BASE_URL}/api/v1/autofill/page/list",
                headers=self.admin_headers(),
                params={"app_name": self.context.app_name, "page": 1, "page_size": 10}
            )
            data = resp.json()
            if data.get("code") == 200:
                self.log(f"获取页面列表成功", "success")
                self.record_result("获取页面列表", True)
            else:
                self.log(f"获取页面列表失败: {data.get('msg')}", "error")
                self.record_result("获取页面列表", False, error=data.get('msg'))
                success = False
        except Exception as e:
            self.log(f"获取页面列表异常: {e}", "error")
            self.record_result("获取页面列表", False, error=str(e))
            success = False
        
        return success
    
    async def test_field_group_management(self) -> bool:
        """测试字段组配置功能"""
        self.log("\n========== 测试字段组配置 ==========")
        success = True
        
        # 1. 创建字段组
        try:
            resp = await self.client.post(
                f"{BASE_URL}/api/v1/autofill/field_group/create",
                headers=self.admin_headers(),
                json={
                    "group_name": self.context.field_group_name,
                    "page_id": self.context.page_id,
                    "description": "完整功能测试字段组",
                    "is_active": True
                }
            )
            data = resp.json()
            if data.get("code") == 200:
                self.context.field_group_id = data["data"]["id"]
                self.log(f"创建字段组成功: ID={self.context.field_group_id}", "success")
                self.record_result("创建字段组", True, f"ID={self.context.field_group_id}")
            else:
                self.log(f"创建字段组失败: {data.get('msg')}", "error")
                self.record_result("创建字段组", False, error=data.get('msg'))
                success = False
        except Exception as e:
            self.log(f"创建字段组异常: {e}", "error")
            self.record_result("创建字段组", False, error=str(e))
            success = False
        
        # 2. 获取字段组列表
        try:
            resp = await self.client.get(
                f"{BASE_URL}/api/v1/autofill/field_group/list",
                headers=self.admin_headers(),
                params={"page_id": self.context.page_id, "page": 1, "page_size": 10}
            )
            data = resp.json()
            if data.get("code") == 200:
                self.log(f"获取字段组列表成功", "success")
                self.record_result("获取字段组列表", True)
            else:
                self.log(f"获取字段组列表失败: {data.get('msg')}", "error")
                self.record_result("获取字段组列表", False, error=data.get('msg'))
                success = False
        except Exception as e:
            self.log(f"获取字段组列表异常: {e}", "error")
            self.record_result("获取字段组列表", False, error=str(e))
            success = False
        
        return success
    
    async def test_field_spec_management(self) -> bool:
        """测试字段明细管理功能"""
        self.log("\n========== 测试字段明细管理 ==========")
        success = True
        
        # 使用带时间戳的字段名避免冲突
        text_field = f"{self.context.field_prefix}customer_name"
        single_field = f"{self.context.field_prefix}scene_category"
        multi_field = f"{self.context.field_prefix}service_types"
        
        # 1. 创建文本字段（使用field_group_ids）
        try:
            resp = await self.client.post(
                f"{BASE_URL}/api/v1/autofill/field_spec/create",
                headers=self.admin_headers(),
                json={
                    "field_name": text_field,
                    "field_label": "客户姓名",
                    "field_type": "text",
                    "app_name": self.context.app_name,
                    "fill_instruction": "请填写客户姓名",
                    "field_group_ids": [self.context.field_group_id],
                    "is_active": True
                }
            )
            data = resp.json()
            if data.get("code") == 200:
                field_id = data["data"]["id"]
                self.context.field_ids.append(field_id)
                self.log(f"创建文本字段成功: ID={field_id}", "success")
                self.record_result("创建文本字段", True, f"ID={field_id}")
            else:
                self.log(f"创建文本字段失败: {data.get('msg')}", "error")
                self.record_result("创建文本字段", False, error=data.get('msg'))
                success = False
        except Exception as e:
            self.log(f"创建文本字段异常: {e}", "error")
            self.record_result("创建文本字段", False, error=str(e))
            success = False
        
        # 2. 创建单选字段（带选项）
        try:
            resp = await self.client.post(
                f"{BASE_URL}/api/v1/autofill/field_spec/create",
                headers=self.admin_headers(),
                json={
                    "field_name": single_field,
                    "field_label": "场景分类",
                    "field_type": "select_single",
                    "app_name": self.context.app_name,
                    "fill_instruction": "请选择场景分类",
                    "options": {
                        "items": [
                            {"label": "道路救援", "value": "rescue", "fill_instruction": "车辆故障或事故需要救援"},
                            {"label": "产品咨询", "value": "consult", "fill_instruction": "咨询产品相关信息"}
                        ]
                    },
                    "field_group_ids": [self.context.field_group_id],
                    "is_active": True
                }
            )
            data = resp.json()
            if data.get("code") == 200:
                field_id = data["data"]["id"]
                self.context.field_ids.append(field_id)
                self.log(f"创建单选字段成功: ID={field_id}", "success")
                self.record_result("创建单选字段", True, f"ID={field_id}")
            else:
                self.log(f"创建单选字段失败: {data.get('msg')}", "error")
                self.record_result("创建单选字段", False, error=data.get('msg'))
                success = False
        except Exception as e:
            self.log(f"创建单选字段异常: {e}", "error")
            self.record_result("创建单选字段", False, error=str(e))
            success = False
        
        # 3. 创建多选字段（带选项）
        try:
            resp = await self.client.post(
                f"{BASE_URL}/api/v1/autofill/field_spec/create",
                headers=self.admin_headers(),
                json={
                    "field_name": multi_field,
                    "field_label": "服务类型",
                    "field_type": "select_multi",
                    "app_name": self.context.app_name,
                    "fill_instruction": "请选择服务类型",
                    "options": {
                        "items": [
                            {"label": "拖车服务", "value": "tow", "fill_instruction": "需要拖车服务"},
                            {"label": "送油服务", "value": "fuel", "fill_instruction": "需要送油服务"},
                            {"label": "换胎服务", "value": "tire", "fill_instruction": "需要换胎服务"}
                        ]
                    },
                    "field_group_ids": [self.context.field_group_id],
                    "is_active": True
                }
            )
            data = resp.json()
            if data.get("code") == 200:
                field_id = data["data"]["id"]
                self.context.field_ids.append(field_id)
                self.log(f"创建多选字段成功: ID={field_id}", "success")
                self.record_result("创建多选字段", True, f"ID={field_id}")
            else:
                self.log(f"创建多选字段失败: {data.get('msg')}", "error")
                self.record_result("创建多选字段", False, error=data.get('msg'))
                success = False
        except Exception as e:
            self.log(f"创建多选字段异常: {e}", "error")
            self.record_result("创建多选字段", False, error=str(e))
            success = False
        
        # 4. 获取字段列表
        try:
            resp = await self.client.get(
                f"{BASE_URL}/api/v1/autofill/field_spec/list",
                headers=self.admin_headers(),
                params={"field_group_id": self.context.field_group_id, "page": 1, "page_size": 10}
            )
            data = resp.json()
            if data.get("code") == 200:
                field_list = data['data'].get('list', []) if isinstance(data['data'], dict) else data['data']
                self.log(f"获取字段列表成功: 共{len(field_list)}个字段", "success")
                self.record_result("获取字段列表", True)
            else:
                self.log(f"获取字段列表失败: {data.get('msg')}", "error")
                self.record_result("获取字段列表", False, error=data.get('msg'))
                success = False
        except Exception as e:
            self.log(f"获取字段列表异常: {e}", "error")
            self.record_result("获取字段列表", False, error=str(e))
            success = False
        
        # 5. 更新字段（测试Markdown选项编辑）
        if len(self.context.field_ids) >= 2:
            try:
                resp = await self.client.post(
                    f"{BASE_URL}/api/v1/autofill/field_spec/update",
                    headers=self.admin_headers(),
                    json={
                        "id": self.context.field_ids[1],
                        "field_label": "场景分类（已更新）",
                        "options": {
                            "items": [
                                {"label": "道路救援", "value": "rescue", "fill_instruction": "车辆故障或事故需要救援"},
                                {"label": "产品咨询", "value": "consult", "fill_instruction": "咨询产品相关信息"},
                                {"label": "投诉建议", "value": "complaint", "fill_instruction": "客户投诉或建议"}
                            ]
                        }
                    }
                )
                data = resp.json()
                if data.get("code") == 200:
                    self.log(f"更新字段成功: ID={self.context.field_ids[1]}", "success")
                    self.record_result("更新字段", True)
                else:
                    self.log(f"更新字段失败: {data.get('msg')}", "error")
                    self.record_result("更新字段", False, error=data.get('msg'))
                    success = False
            except Exception as e:
                self.log(f"更新字段异常: {e}", "error")
                self.record_result("更新字段", False, error=str(e))
                success = False
        
        return success
    
    # ==================== 第二阶段：Public填单功能测试 ====================
    
    async def test_public_field_group_query(self) -> bool:
        """测试Public字段组查询接口"""
        self.log("\n========== 测试Public字段组查询 ==========")
        success = True
        
        if not self.context.api_key:
            self.log("API Key 为空，跳过Public测试", "warning")
            return False
        
        # 1. 查询字段组配置
        try:
            resp = await self.client.post(
                f"{BASE_URL}/api/autofill/field_group",
                headers=self.public_headers(),
                json={
                    "app_name": self.context.app_name,
                    "page_name": self.context.page_name,
                    "field_group_name": self.context.field_group_name
                }
            )
            data = resp.json()
            if data.get("code") == 200:
                self.log(f"查询字段组配置成功", "success")
                self.record_result("Public-查询字段组配置", True)
            else:
                self.log(f"查询字段组配置失败: {data.get('msg')}", "error")
                self.record_result("Public-查询字段组配置", False, error=data.get('msg'))
                success = False
        except Exception as e:
            self.log(f"查询字段组配置异常: {e}", "error")
            self.record_result("Public-查询字段组配置", False, error=str(e))
            success = False
        
        # 2. 获取合并后的Function Calling Schema
        try:
            resp = await self.client.post(
                f"{BASE_URL}/api/autofill/field_groups/schema",
                headers=self.public_headers(),
                json={
                    "app_name": self.context.app_name,
                    "page_name": self.context.page_name,
                    "group_names": [self.context.field_group_name]
                }
            )
            data = resp.json()
            if data.get("code") == 200:
                self.log(f"获取Function Calling Schema成功", "success")
                fields = data['data'].get('fields', []) if isinstance(data['data'], dict) else []
                self.log(f"Schema字段数: {len(fields)}", "info")
                self.record_result("Public-获取Function Calling Schema", True)
            else:
                self.log(f"获取Function Calling Schema失败: {data.get('msg')}", "error")
                self.record_result("Public-获取Function Calling Schema", False, error=data.get('msg'))
                success = False
        except Exception as e:
            self.log(f"获取Function Calling Schema异常: {e}", "error")
            self.record_result("Public-获取Function Calling Schema", False, error=str(e))
            success = False
        
        return success
    
    async def test_public_llm_fill(self) -> bool:
        """测试Public LLM填单接口"""
        self.log("\n========== 测试Public LLM填单 ==========")
        success = True
        
        if not self.context.api_key:
            self.log("API Key 为空，跳过Public测试", "warning")
            return False
        
        # 使用带时间戳的字段名
        text_field = f"{self.context.field_prefix}customer_name"
        
        # 1. 单字段填单
        try:
            resp = await self.client.post(
                f"{BASE_URL}/api/autofill/llm/fill",
                headers=self.public_headers(),
                json={
                    "app_name": self.context.app_name,
                    "page_name": self.context.page_name,
                    "group_names": [self.context.field_group_name],
                    "field_names": [text_field],
                    "query": "客户姓名是张三"
                }
            )
            data = resp.json()
            if data.get("code") == 200:
                self.log(f"单字段填单成功: {data['data']}", "success")
                self.record_result("Public-单字段填单", True)
            else:
                self.log(f"单字段填单失败: {data.get('msg')}", "error")
                self.record_result("Public-单字段填单", False, error=data.get('msg'))
                success = False
        except Exception as e:
            self.log(f"单字段填单异常: {e}", "error")
            self.record_result("Public-单字段填单", False, error=str(e))
            success = False
        
        # 2. 多字段填单
        try:
            resp = await self.client.post(
                f"{BASE_URL}/api/autofill/llm/fill",
                headers=self.public_headers(),
                json={
                    "app_name": self.context.app_name,
                    "page_name": self.context.page_name,
                    "group_names": [self.context.field_group_name],
                    "query": "客户张三的车在高速上抛锚了，需要拖车和送油服务"
                }
            )
            data = resp.json()
            if data.get("code") == 200:
                self.log(f"多字段填单成功: {data['data']}", "success")
                self.record_result("Public-多字段填单", True)
            else:
                self.log(f"多字段填单失败: {data.get('msg')}", "error")
                self.record_result("Public-多字段填单", False, error=data.get('msg'))
                success = False
        except Exception as e:
            self.log(f"多字段填单异常: {e}", "error")
            self.record_result("Public-多字段填单", False, error=str(e))
            success = False
        
        return success
    
    async def test_public_ai_fill(self) -> bool:
        """测试Public AI填单接口"""
        self.log("\n========== 测试Public AI填单 ==========")
        success = True
        
        if not self.context.api_key:
            self.log("API Key 为空，跳过Public测试", "warning")
            return False
        
        # AI填单 - 使用正确的接口路径
        try:
            resp = await self.client.post(
                f"{BASE_URL}/api/autofill/get_ai_fill_data",
                headers=self.public_headers(),
                json={
                    "app_name": self.context.app_name,
                    "page_name": self.context.page_name,
                    "group_names": [self.context.field_group_name],
                    "query": "客户李四的车轮胎爆了，需要换胎服务，位置在北京市朝阳区",
                    "session_id": f"test_session_{self.context.field_prefix}",
                    "data": {}
                }
            )
            data = resp.json()
            if data.get("code") == 200:
                self.log(f"AI填单成功: {data['data']}", "success")
                self.record_result("Public-AI填单", True)
            else:
                self.log(f"AI填单失败: {data.get('msg')}", "error")
                self.record_result("Public-AI填单", False, error=data.get('msg'))
                success = False
        except Exception as e:
            self.log(f"AI填单异常: {e}", "error")
            self.record_result("Public-AI填单", False, error=str(e))
            success = False
        
        return success
    
    # ==================== 清理工作 ====================
    
    async def cleanup(self):
        """清理测试数据"""
        self.log("\n========== 清理测试数据 ==========")
        
        # 删除字段
        for field_id in self.context.field_ids:
            try:
                await self.client.post(
                    f"{BASE_URL}/api/v1/autofill/field_spec/delete",
                    headers=self.admin_headers(),
                    json={"id": field_id}
                )
                self.log(f"删除字段: ID={field_id}", "success")
            except Exception as e:
                self.log(f"删除字段失败: {e}", "warning")
        
        # 删除字段组
        if self.context.field_group_id:
            try:
                await self.client.post(
                    f"{BASE_URL}/api/v1/autofill/field_group/delete",
                    headers=self.admin_headers(),
                    json={"id": self.context.field_group_id}
                )
                self.log(f"删除字段组: ID={self.context.field_group_id}", "success")
            except Exception as e:
                self.log(f"删除字段组失败: {e}", "warning")
        
        # 删除页面
        if self.context.page_id:
            try:
                await self.client.post(
                    f"{BASE_URL}/api/v1/autofill/page/delete",
                    headers=self.admin_headers(),
                    json={"id": self.context.page_id}
                )
                self.log(f"删除页面: ID={self.context.page_id}", "success")
            except Exception as e:
                self.log(f"删除页面失败: {e}", "warning")
        
        # 如果是新创建的应用，删除应用
        if self.context.app_id and not self.context.use_existing_app:
            try:
                await self.client.post(
                    f"{BASE_URL}/api/v1/autofill/app/delete",
                    headers=self.admin_headers(),
                    json={"id": self.context.app_id}
                )
                self.log(f"删除应用: ID={self.context.app_id}", "success")
            except Exception as e:
                self.log(f"删除应用失败: {e}", "warning")
    
    def print_summary(self):
        """打印测试摘要"""
        self.log("\n" + "="*60)
        self.log("测试摘要")
        self.log("="*60)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["success"])
        failed = total - passed
        
        self.log(f"总计: {total} 个测试")
        self.log(f"通过: {passed} 个", "success")
        self.log(f"失败: {failed} 个", "error" if failed > 0 else "info")
        
        if failed > 0:
            self.log("\n失败的测试:")
            for result in self.test_results:
                if not result["success"]:
                    self.log(f"  - {result['name']}: {result.get('error', '未知错误')}", "error")
        
        return failed == 0
    
    async def run_all_tests(self) -> bool:
        """运行所有测试"""
        self.log("="*60)
        self.log("智能填单系统 - 完整功能测试")
        self.log("="*60)
        
        # 1. 登录
        if not await self.admin_login():
            return False
        
        # 2. 后端管理功能测试
        await self.test_app_management()
        await self.test_page_management()
        await self.test_field_group_management()
        await self.test_field_spec_management()
        
        # 3. Public填单功能测试
        await self.test_public_field_group_query()
        await self.test_public_llm_fill()
        await self.test_public_ai_fill()
        
        # 4. 打印摘要
        return self.print_summary()


async def main():
    """主函数"""
    async with FullSystemTester() as tester:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
