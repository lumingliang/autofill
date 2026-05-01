#!/usr/bin/env python3
"""
400客服道路救援场景 - 完整测试脚本

场景描述:
400客服中心接到车主道路救援请求，需要记录:
1. 业务类型(道路救援)
2. 服务记录详情(包含多个子字段)
3. 最终通过模板生成标准服务记录文本

测试内容:
1. 创建应用、页面、字段组
2. 配置字段明细(包含select和text类型)
3. 配置服务记录模板
4. 测试LLM填单功能
5. 验证模板渲染结果

使用方法:
    # 先确保后端服务已启动
    python test_roadside_rescue_scenario.py

环境变量:
    BASE_URL: 后端服务地址 (默认: http://127.0.0.1:9999)
    ADMIN_TOKEN: 管理员JWT Token (用于管理接口)
    API_KEY: 应用API Key (用于公开接口，脚本会自动创建)
"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx


@dataclass
class TestContext:
    """测试上下文，保存测试过程中创建的资源ID"""
    tenant_id: int = 1
    app_id: Optional[int] = None
    app_name: str = "roadside_rescue"
    api_key: Optional[str] = None
    page_id: Optional[int] = None
    page_code: str = "rescue_workbench"
    field_group_id: Optional[int] = None
    field_group_code: Optional[str] = None
    field_ids: List[int] = field(default_factory=list)
    template_id: Optional[int] = None


@dataclass
class TestResult:
    """测试结果"""
    name: str
    success: bool
    status_code: int
    response: Any
    error: Optional[str] = None
    duration_ms: float = 0


class RoadsideRescueScenarioTest:
    """道路救援场景测试器"""

    def __init__(self):
        self.base_url = os.getenv("BASE_URL", "http://127.0.0.1:9999")
        self.admin_token = os.getenv("ADMIN_TOKEN", "")
        self.context = TestContext()
        self.results: List[TestResult] = []

        # 管理员接口Headers (使用JWT Token)
        self.admin_headers = {
            "Content-Type": "application/json",
            "token": self.admin_token,
        }

        # API前缀
        self.admin_api_prefix = "/api/v1"  # 管理接口前缀
        self.public_api_prefix = "/api"    # 公开接口前缀

        # 公开接口Headers (在创建应用后设置)
        self.public_headers = {
            "Content-Type": "application/json",
        }

    async def _admin_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> tuple[int, Any, float]:
        """发送管理员接口请求"""
        import time

        # 自动添加管理接口前缀
        if not endpoint.startswith(self.admin_api_prefix):
            endpoint = f"{self.admin_api_prefix}{endpoint}"

        url = f"{self.base_url}{endpoint}"
        start = time.time()

        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=self.admin_headers, params=params)
            else:
                response = await client.post(url, headers=self.admin_headers, json=data)

        duration = (time.time() - start) * 1000

        try:
            resp_data = response.json()
        except:
            resp_data = response.text

        return response.status_code, resp_data, duration

    async def _public_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> tuple[int, Any, float]:
        """发送公开接口请求"""
        import time

        # 自动添加公开接口前缀
        if not endpoint.startswith(self.public_api_prefix):
            endpoint = f"{self.public_api_prefix}{endpoint}"

        url = f"{self.base_url}{endpoint}"
        start = time.time()

        # 确保使用API Key认证
        headers = self.public_headers.copy()
        if self.context.api_key:
            headers["Authorization"] = f"Bearer {self.context.api_key}"
            headers["X-Tenant-ID"] = str(self.context.tenant_id)

        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, params=params)
            else:
                response = await client.post(url, headers=headers, json=data)

        duration = (time.time() - start) * 1000

        try:
            resp_data = response.json()
        except:
            resp_data = response.text

        return response.status_code, resp_data, duration

    def _add_result(
        self,
        name: str,
        success: bool,
        status_code: int,
        response: Any,
        error: Optional[str] = None,
        duration_ms: float = 0,
    ):
        """添加测试结果"""
        result = TestResult(
            name=name,
            success=success,
            status_code=status_code,
            response=response,
            error=error,
            duration_ms=duration_ms,
        )
        self.results.append(result)
        return result

    def _print_step(self, step_num: int, title: str):
        """打印步骤标题"""
        print(f"\n{'='*60}")
        print(f"步骤 {step_num}: {title}")
        print('='*60)

    def _print_substep(self, title: str):
        """打印子步骤"""
        print(f"\n  ▸ {title}")

    # ==================== 步骤1: 创建应用 ====================
    async def step1_create_app(self):
        """步骤1: 创建应用"""
        self._print_step(1, "创建应用")

        # 先检查应用是否已存在
        self._print_substep("检查应用是否已存在...")
        status_code, response, _ = await self._admin_request(
            "GET", "/api/autofill/app/list",
            params={"app_name": self.context.app_name, "page_size": 100}
        )

        if status_code == 200 and response.get("code") == 200:
            apps = response.get("data", [])
            for app in apps:
                if app.get("app_name") == self.context.app_name:
                    self.context.app_id = app.get("id")
                    self.context.api_key = app.get("api_key")
                    print(f"  ✓ 应用已存在: ID={self.context.app_id}, API Key={self.context.api_key}")
                    self._add_result("创建应用", True, status_code, app, duration_ms=0)
                    return True

        # 创建新应用
        self._print_substep("创建新应用...")
        app_data = {
            "app_name": self.context.app_name,
            "tenant_id": self.context.tenant_id,
            "description": "400客服道路救援系统",
            "dify_url": "",
            "dify_api_key": ""
        }

        status_code, response, duration = await self._admin_request(
            "POST", "/api/autofill/app/create", data=app_data
        )

        if status_code == 200 and response.get("code") == 200:
            data = response.get("data", {})
            self.context.app_id = data.get("id")
            self.context.api_key = data.get("api_key")
            print(f"  ✓ 应用创建成功")
            print(f"    - ID: {self.context.app_id}")
            print(f"    - 名称: {data.get('app_name')}")
            print(f"    - API Key: {self.context.api_key}")
            self._add_result("创建应用", True, status_code, data, duration_ms=duration)
            return True
        else:
            error_msg = response.get("msg", "Unknown error")
            print(f"  ✗ 应用创建失败: {error_msg}")
            self._add_result("创建应用", False, status_code, response, error=error_msg, duration_ms=duration)
            return False

    # ==================== 步骤2: 创建页面 ====================
    async def step2_create_page(self):
        """步骤2: 创建填单页面"""
        self._print_step(2, "创建填单页面")

        # 检查页面是否已存在
        self._print_substep("检查页面是否已存在...")
        status_code, response, _ = await self._admin_request(
            "GET", "/api/autofill/page/list",
            params={"page_code": self.context.page_code, "page_size": 100}
        )

        if status_code == 200 and response.get("code") == 200:
            pages = response.get("data", [])
            for page in pages:
                if page.get("page_code") == self.context.page_code:
                    self.context.page_id = page.get("id")
                    print(f"  ✓ 页面已存在: ID={self.context.page_id}")
                    self._add_result("创建页面", True, status_code, page, duration_ms=0)
                    return True

        # 创建新页面
        self._print_substep("创建新页面...")
        page_data = {
            "page_name": "道路救援工作台",
            "page_code": self.context.page_code,
            "app_id": self.context.app_id,
            "tenant_id": self.context.tenant_id,
            "description": "400客服道路救援话务工作台",
            "is_active": True
        }

        status_code, response, duration = await self._admin_request(
            "POST", "/api/autofill/page/create", data=page_data
        )

        if status_code == 200 and response.get("code") == 200:
            data = response.get("data", {})
            self.context.page_id = data.get("id")
            print(f"  ✓ 页面创建成功")
            print(f"    - ID: {self.context.page_id}")
            print(f"    - 名称: {data.get('page_name')}")
            print(f"    - 编码: {data.get('page_code')}")
            self._add_result("创建页面", True, status_code, data, duration_ms=duration)
            return True
        else:
            error_msg = response.get("msg", "Unknown error")
            print(f"  ✗ 页面创建失败: {error_msg}")
            self._add_result("创建页面", False, status_code, response, error=error_msg, duration_ms=duration)
            return False

    # ==================== 步骤3: 创建字段组 ====================
    async def step3_create_field_group(self):
        """步骤3: 创建字段组配置"""
        self._print_step(3, "创建字段组配置")

        # 检查字段组是否已存在
        self._print_substep("检查字段组是否已存在...")
        status_code, response, _ = await self._admin_request(
            "GET", "/api/autofill/field_group/list",
            params={"page_id": self.context.page_id, "page_size": 100}
        )

        if status_code == 200 and response.get("code") == 200:
            groups = response.get("data", [])
            for group in groups:
                if group.get("page_id") == self.context.page_id:
                    self.context.field_group_id = group.get("id")
                    self.context.field_group_code = group.get("group_code")
                    print(f"  ✓ 字段组已存在: ID={self.context.field_group_id}, Code={self.context.field_group_code}")
                    self._add_result("创建字段组", True, status_code, group, duration_ms=0)
                    return True

        # 创建Prompt基础模板
        prompt_template = """你是一个专业的400客服道路救援信息提取助手。

请根据客服与车主的对话内容，提取以下道路救援相关信息：

{{fields_instructions}}

对话内容：
{{query}}

提取规则：
1. 仔细分析对话内容，准确提取每个字段的信息
2. 如果某个字段信息未提及，返回空字符串
3. 对于选择字段，必须从可选值中选择最匹配的一项
4. 联系电话优先提取手机号，如果没有则提取固话
5. 故障现象根据用户描述选择最接近的选项

请以JSON格式返回提取结果。"""

        # 创建输出模板配置
        output_templates = {
            "service_record": {
                "template": "车主{{customer_name}}（{{caller_relation}}）{{contact_phone}}请求道路救援。车系：{{vehicle_system}}，车架号：{{vin_code}}。车辆故障现象：{{fault_phenomenon}}。车辆当前位置：{{vehicle_location}}。是否安全停放：{{is_parked_safely}}，是否影响交通：{{is_affecting_traffic}}。车上人数：{{passenger_count}}人。客户联系电话：{{contact_phone}}（备用电话：{{backup_phone}}）。期望救援时间：{{expected_rescue_time}}。拖车目的地：{{tow_destination}}。已告知客户预计到达时间并安排救援。",
                "description": "标准服务记录文本"
            }
        }

        # 创建新字段组
        self._print_substep("创建新字段组...")
        group_data = {
            "group_name": "道路救援服务记录",
            "group_code": f"rescue_group_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "page_id": self.context.page_id,
            "prompt_template_base": prompt_template,
            "output_templates": output_templates,
            "description": "400客服道路救援服务记录字段组",
            "tenant_id": self.context.tenant_id,
            "is_active": True
        }

        status_code, response, duration = await self._admin_request(
            "POST", "/api/autofill/field_group/create", data=group_data
        )

        if status_code == 200 and response.get("code") == 200:
            data = response.get("data", {})
            self.context.field_group_id = data.get("id")
            self.context.field_group_code = data.get("group_code")
            print(f"  ✓ 字段组创建成功")
            print(f"    - ID: {self.context.field_group_id}")
            print(f"    - 名称: {data.get('group_name')}")
            print(f"    - 编码: {data.get('group_code')}")
            self._add_result("创建字段组", True, status_code, data, duration_ms=duration)
            return True
        else:
            error_msg = response.get("msg", "Unknown error")
            print(f"  ✗ 字段组创建失败: {error_msg}")
            self._add_result("创建字段组", False, status_code, response, error=error_msg, duration_ms=duration)
            return False

    # ==================== 步骤4: 创建字段明细 ====================
    async def step4_create_field_specs(self):
        """步骤4: 创建字段明细"""
        self._print_step(4, "创建字段明细")

        # 先获取现有字段
        self._print_substep("检查现有字段...")
        status_code, response, _ = await self._admin_request(
            "GET", "/api/autofill/field_spec/by_group",
            params={"field_group_id": self.context.field_group_id}
        )

        existing_fields = {}
        if status_code == 200 and response.get("code") == 200:
            fields = response.get("data", [])
            for field in fields:
                existing_fields[field.get("field_name")] = field.get("id")
            if fields:
                print(f"  ✓ 字段组已有 {len(fields)} 个字段")
                self.context.field_ids = [f.get("id") for f in fields]

        # 定义要创建的字段
        field_definitions = [
            # 业务类型字段
            {
                "field_name": "business_type",
                "field_label": "业务类型",
                "field_type": "select",
                "fill_instruction": "选择业务类型",
                "options": {
                    "source": "static",
                    "items": [
                        {"value": "road_rescue", "label": "道路救援", "base_annotation": "道路救援服务"},
                        {"value": "consultation", "label": "业务咨询", "base_annotation": "一般业务咨询"},
                        {"value": "complaint", "label": "投诉建议", "base_annotation": "客户投诉或建议"}
                    ]
                }
            },
            # 来电人身份
            {
                "field_name": "caller_relation",
                "field_label": "来电人身份",
                "field_type": "select",
                "fill_instruction": "选择来电人与车主的关系",
                "options": {
                    "source": "static",
                    "items": [
                        {"value": "owner", "label": "本人", "base_annotation": "车主本人"},
                        {"value": "family", "label": "家人", "base_annotation": "车主家人"},
                        {"value": "friend", "label": "朋友", "base_annotation": "车主朋友"},
                        {"value": "colleague", "label": "同事", "base_annotation": "车主同事"},
                        {"value": "other", "label": "其他", "base_annotation": "其他关系"}
                    ]
                }
            },
            # 客户姓名
            {
                "field_name": "customer_name",
                "field_label": "客户姓名",
                "field_type": "text",
                "fill_instruction": "提取客户姓名，如'张先生'、'李女士'等"
            },
            # 联系电话
            {
                "field_name": "contact_phone",
                "field_label": "联系电话",
                "field_type": "text",
                "fill_instruction": "提取客户联系电话，优先提取手机号码"
            },
            # 备用电话
            {
                "field_name": "backup_phone",
                "field_label": "备用电话",
                "field_type": "text",
                "fill_instruction": "提取备用联系电话，如果没有则留空"
            },
            # 车系
            {
                "field_name": "vehicle_system",
                "field_label": "车系",
                "field_type": "text",
                "fill_instruction": "提取车辆品牌和型号，如'奥迪A6'、'宝马X5'等"
            },
            # VIN码
            {
                "field_name": "vin_code",
                "field_label": "车架号(VIN)",
                "field_type": "text",
                "fill_instruction": "提取17位车辆识别号码(VIN码)"
            },
            # 故障现象
            {
                "field_name": "fault_phenomenon",
                "field_label": "故障现象",
                "field_type": "select",
                "fill_instruction": "根据客户描述选择最匹配的故障现象",
                "options": {
                    "source": "static",
                    "items": [
                        {"value": "cannot_start", "label": "无法启动", "base_annotation": "车辆无法启动"},
                        {"value": "accident", "label": "事故", "base_annotation": "发生交通事故"},
                        {"value": "flat_tire", "label": "爆胎", "base_annotation": "轮胎爆胎"},
                        {"value": "out_of_fuel", "label": "缺油", "base_annotation": "车辆燃油耗尽"},
                        {"value": "battery", "label": "搭电", "base_annotation": "电瓶亏电需要搭电"},
                        {"value": "other", "label": "其他", "base_annotation": "其他故障情况"}
                    ]
                }
            },
            # 车辆位置
            {
                "field_name": "vehicle_location",
                "field_label": "车辆位置",
                "field_type": "text",
                "fill_instruction": "提取车辆当前详细位置地址"
            },
            # 是否安全停放
            {
                "field_name": "is_parked_safely",
                "field_label": "是否安全停放",
                "field_type": "select",
                "fill_instruction": "选择车辆是否停放在安全位置",
                "options": {
                    "source": "static",
                    "items": [
                        {"value": "yes", "label": "是", "base_annotation": "车辆已安全停放"},
                        {"value": "no", "label": "否", "base_annotation": "车辆未安全停放"}
                    ]
                }
            },
            # 是否影响交通
            {
                "field_name": "is_affecting_traffic",
                "field_label": "是否影响交通",
                "field_type": "select",
                "fill_instruction": "选择车辆是否影响道路交通",
                "options": {
                    "source": "static",
                    "items": [
                        {"value": "yes", "label": "是", "base_annotation": "车辆影响交通通行"},
                        {"value": "no", "label": "否", "base_annotation": "车辆不影响交通"}
                    ]
                }
            },
            # 车上人数
            {
                "field_name": "passenger_count",
                "field_label": "车上人数",
                "field_type": "text",
                "fill_instruction": "提取车上人员数量，仅填写数字"
            },
            # 期望救援时间
            {
                "field_name": "expected_rescue_time",
                "field_label": "期望救援时间",
                "field_type": "select",
                "fill_instruction": "选择客户期望的救援时间",
                "options": {
                    "source": "static",
                    "items": [
                        {"value": "immediate", "label": "立即", "base_annotation": "需要立即救援"},
                        {"value": "scheduled", "label": "预约时间", "base_annotation": "预约指定时间"}
                    ]
                }
            },
            # 拖车目的地
            {
                "field_name": "tow_destination",
                "field_label": "拖车目的地",
                "field_type": "select",
                "fill_instruction": "选择拖车目的地类型",
                "options": {
                    "source": "static",
                    "items": [
                        {"value": "4s_shop", "label": "4S店", "base_annotation": "拖至4S店维修"},
                        {"value": "specified_address", "label": "指定地址", "base_annotation": "拖至客户指定地址"}
                    ]
                }
            }
        ]

        created_count = 0
        for field_def in field_definitions:
            field_name = field_def["field_name"]

            # 检查字段是否已存在
            if field_name in existing_fields:
                print(f"  ✓ 字段已存在: {field_name}")
                if existing_fields[field_name] not in self.context.field_ids:
                    self.context.field_ids.append(existing_fields[field_name])
                continue

            # 创建字段
            field_data = {
                "field_group_id": self.context.field_group_id,
                **field_def
            }

            status_code, response, duration = await self._admin_request(
                "POST", "/api/autofill/field_spec/create", data=field_data
            )

            if status_code == 200 and response.get("code") == 200:
                data = response.get("data", {})
                field_id = data.get("id")
                self.context.field_ids.append(field_id)
                created_count += 1
                print(f"  ✓ 创建字段: {field_name} ({data.get('field_label')})")
            else:
                error_msg = response.get("msg", "Unknown error")
                print(f"  ✗ 创建字段失败 {field_name}: {error_msg}")
                self._add_result(f"创建字段-{field_name}", False, status_code, response, error=error_msg, duration_ms=duration)

        if created_count > 0 or len(self.context.field_ids) > 0:
            self._add_result("创建字段明细", True, 200, {"created": created_count, "total": len(self.context.field_ids)})
            print(f"\n  总计: {len(self.context.field_ids)} 个字段")
            return True
        else:
            self._add_result("创建字段明细", False, 500, {}, error="未创建任何字段")
            return False

    # ==================== 步骤5: 创建总结模板 ====================
    async def step5_create_summary_template(self):
        """步骤5: 创建总结模板"""
        self._print_step(5, "创建总结模板")

        # 检查模板是否已存在
        self._print_substep("检查模板是否已存在...")
        status_code, response, _ = await self._admin_request(
            "GET", "/api/autofill/template/list",
            params={"app_name": self.context.app_name, "page_size": 100}
        )

        if status_code == 200 and response.get("code") == 200:
            templates = response.get("data", [])
            for template in templates:
                if template.get("name") == "道路救援服务记录模板":
                    self.context.template_id = template.get("id")
                    print(f"  ✓ 模板已存在: ID={self.context.template_id}")
                    self._add_result("创建总结模板", True, status_code, template, duration_ms=0)
                    return True

        # 创建新模板
        self._print_substep("创建新模板...")
        template_content = """车主${customer_name}（${caller_relation}）${contact_phone}请求道路救援。车系：${vehicle_system}，车架号：${vin_code}。车辆故障现象：${fault_phenomenon}。车辆当前位置：${vehicle_location}。是否安全停放：${is_parked_safely}，是否影响交通：${is_affecting_traffic}。车上人数：${passenger_count}人。客户联系电话：${contact_phone}（备用电话：${backup_phone}）。期望救援时间：${expected_rescue_time}。拖车目的地：${tow_destination}。已告知客户预计到达时间并安排救援。"""

        template_data = {
            "name": "道路救援服务记录模板",
            "app_name": self.context.app_name,
            "tenant_id": self.context.tenant_id,
            "class_name": "service_record",
            "summary": "400客服道路救援标准服务记录模板",
            "template_content": template_content
        }

        status_code, response, duration = await self._admin_request(
            "POST", "/api/autofill/template/create", data=template_data
        )

        if status_code == 200 and response.get("code") == 200:
            data = response.get("data", {})
            self.context.template_id = data.get("id")
            print(f"  ✓ 模板创建成功")
            print(f"    - ID: {self.context.template_id}")
            print(f"    - 名称: {data.get('name')}")
            self._add_result("创建总结模板", True, status_code, data, duration_ms=duration)
            return True
        else:
            error_msg = response.get("msg", "Unknown error")
            print(f"  ✗ 模板创建失败: {error_msg}")
            self._add_result("创建总结模板", False, status_code, response, error=error_msg, duration_ms=duration)
            return False

    # ==================== 步骤6: 测试公开接口 - 查询字段组 ====================
    async def step6_test_public_field_group(self):
        """步骤6: 测试公开接口 - 查询字段组"""
        self._print_step(6, "测试公开接口 - 查询字段组")

        self._print_substep("通过API Key查询字段组...")
        status_code, response, duration = await self._public_request(
            "POST", "/api/autofill/field_group",
            data={"page_code": self.context.page_code}
        )

        if status_code == 200 and response.get("code") == 200:
            data = response.get("data", [])
            print(f"  ✓ 成功获取 {len(data)} 个字段组")
            for group in data:
                print(f"    - {group.get('group_name')} (ID: {group.get('id')})")
            self._add_result("公开接口-查询字段组", True, status_code, response, duration_ms=duration)
            return True
        else:
            error_msg = response.get("msg", "Unknown error")
            print(f"  ✗ 查询失败: {error_msg}")
            self._add_result("公开接口-查询字段组", False, status_code, response, error=error_msg, duration_ms=duration)
            return False

    # ==================== 步骤7: 测试公开接口 - 查询字段明细 ====================
    async def step7_test_public_field_spec(self):
        """步骤7: 测试公开接口 - 查询字段明细"""
        self._print_step(7, "测试公开接口 - 查询字段明细")

        self._print_substep("通过API Key查询字段明细...")
        status_code, response, duration = await self._public_request(
            "POST", "/api/autofill/field_spec/list",
            data={"field_group_id": self.context.field_group_id}
        )

        if status_code == 200 and response.get("code") == 200:
            data = response.get("data", [])
            print(f"  ✓ 成功获取 {len(data)} 个字段")

            # 按类型统计
            select_count = sum(1 for f in data if f.get("field_type") == "select")
            text_count = sum(1 for f in data if f.get("field_type") == "text")
            print(f"    - select类型: {select_count} 个")
            print(f"    - text类型: {text_count} 个")

            # 显示字段列表
            print(f"\n  字段列表:")
            for field in data:
                status = "启用" if field.get("is_active") else "禁用"
                print(f"    - {field.get('field_name')}: {field.get('field_label')} ({field.get('field_type')}) [{status}]")

            self._add_result("公开接口-查询字段明细", True, status_code, response, duration_ms=duration)
            return True
        else:
            error_msg = response.get("msg", "Unknown error")
            print(f"  ✗ 查询失败: {error_msg}")
            self._add_result("公开接口-查询字段明细", False, status_code, response, error=error_msg, duration_ms=duration)
            return False

    # ==================== 步骤8: 测试LLM填单 ====================
    async def step8_test_llm_fill(self):
        """步骤8: 测试LLM填单功能"""
        self._print_step(8, "测试LLM填单功能")

        # 测试用例
        test_cases = [
            {
                "name": "标准道路救援请求",
                "query": "你好，我是张先生，我的车在朝阳区建国路这边抛锚了，无法启动。我是车主本人，我的电话是13800138000，车架号是LSVAG2180E2100001，车型是奥迪A6。车上就我一个人，车停在路边，不影响交通。我需要立即救援，拖到4S店去维修。"
            },
            {
                "name": "家人代打电话",
                "query": "喂，我帮我老公打电话，他的车在高速上爆胎了。他姓李，电话是13912345678，车型是宝马X5，车架号WBAKB210X0F123456。现在车停在应急车道上，比较安全，不影响其他车辆。车上有3个人。希望能尽快救援，拖到最近的4S店。"
            },
            {
                "name": "电瓶亏电",
                "query": "您好，我的车电瓶没电了，需要搭电。我姓王，电话是13700137000。车是奔驰C200，车架号是WDDWF4CB3JR123456，在朝阳区三里屯这边。车停在停车场里，很安全。希望马上来人处理。"
            }
        ]

        all_success = True
        for test_case in test_cases:
            print(f"\n  测试用例: {test_case['name']}")
            print(f"  输入: {test_case['query'][:80]}...")

            status_code, response, duration = await self._public_request(
                "POST", "/api/autofill/llm/fill",
                data={
                    "field_group_id": self.context.field_group_id,
                    "input_data": {"query": test_case["query"]}
                }
            )

            if status_code == 200 and response.get("code") == 200:
                data = response.get("data", {})
                result = data.get("result", {})
                meta = data.get("_meta", {})

                print(f"  ✓ 填单成功")
                print(f"    提取结果:")

                # 显示关键字段
                key_fields = ["customer_name", "caller_relation", "contact_phone", 
                             "vehicle_system", "vin_code", "fault_phenomenon", 
                             "vehicle_location", "tow_destination"]
                for field in key_fields:
                    value = result.get(field, "")
                    if value:
                        print(f"      - {field}: {value}")

                # 显示元信息
                if meta:
                    print(f"    元信息:")
                    print(f"      - 模型: {meta.get('model', 'unknown')}")
                    print(f"      - 耗时: {meta.get('latency_ms', 0)}ms")

                # 渲染服务记录模板
                if result:
                    service_record = self._render_service_template(result)
                    print(f"    生成服务记录:")
                    print(f"      {service_record[:100]}...")

                self._add_result(f"LLM填单-{test_case['name']}", True, status_code, response, duration_ms=duration)
            else:
                error_msg = response.get("msg", "Unknown error")
                print(f"  ✗ 填单失败: {error_msg}")
                self._add_result(f"LLM填单-{test_case['name']}", False, status_code, response, error=error_msg, duration_ms=duration)
                all_success = False

        return all_success

    def _render_service_template(self, data: Dict[str, str]) -> str:
        """渲染服务记录模板"""
        template = "车主${customer_name}（${caller_relation}）${contact_phone}请求道路救援。车系：${vehicle_system}，车架号：${vin_code}。车辆故障现象：${fault_phenomenon}。车辆当前位置：${vehicle_location}。是否安全停放：${is_parked_safely}，是否影响交通：${is_affecting_traffic}。车上人数：${passenger_count}人。客户联系电话：${contact_phone}（备用电话：${backup_phone}）。期望救援时间：${expected_rescue_time}。拖车目的地：${tow_destination}。已告知客户预计到达时间并安排救援。"

        result = template
        for key, value in data.items():
            placeholder = f"${{{key}}}"
            result = result.replace(placeholder, str(value) if value else "")

        return result

    # ==================== 步骤9: 测试总结模板接口 ====================
    async def step9_test_summary_template(self):
        """步骤9: 测试总结模板接口"""
        self._print_step(9, "测试总结模板接口")

        self._print_substep("查询模板列表...")
        status_code, response, duration = await self._public_request(
            "POST", "/api/autofill/summary_template/list",
            data={"class_name": "service_record"}
        )

        if status_code == 200 and response.get("code") == 200:
            data = response.get("data", [])
            print(f"  ✓ 成功获取 {len(data)} 个模板")
            for template in data:
                print(f"    - {template.get('name')} (ID: {template.get('id')})")
            self._add_result("模板接口-列表", True, status_code, response, duration_ms=duration)
        else:
            error_msg = response.get("msg", "Unknown error")
            print(f"  ✗ 查询失败: {error_msg}")
            self._add_result("模板接口-列表", False, status_code, response, error=error_msg, duration_ms=duration)
            return False

        # 查询模板详情
        if self.context.template_id:
            self._print_substep("查询模板详情...")
            status_code, response, duration = await self._public_request(
                "POST", "/api/autofill/summary_template",
                data={"id": self.context.template_id}
            )

            if status_code == 200 and response.get("code") == 200:
                data = response.get("data", {})
                print(f"  ✓ 成功获取模板详情")
                print(f"    - 名称: {data.get('name')}")
                print(f"    - 分类: {data.get('class_name')}")
                print(f"    - 内容预览: {data.get('template_content', '')[:80]}...")
                self._add_result("模板接口-详情", True, status_code, response, duration_ms=duration)
                return True
            else:
                error_msg = response.get("msg", "Unknown error")
                print(f"  ✗ 查询失败: {error_msg}")
                self._add_result("模板接口-详情", False, status_code, response, error=error_msg, duration_ms=duration)
                return False

        return True

    # ==================== 步骤10: 测试填单记录接口 ====================
    async def step10_test_record_fill_data(self):
        """步骤10: 测试填单记录接口"""
        self._print_step(10, "测试填单记录接口")

        session_id = f"test_session_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        self._print_substep("记录填单数据...")
        record_data = {
            "session_id": session_id,
            "phone": "13800138000",
            "user_unique_id": "user_001",
            "user_name": "张先生",
            "data": {
                "customer_name": "张先生",
                "contact_phone": "13800138000",
                "vehicle_system": "奥迪A6",
                "vin_code": "LSVAG2180E2100001",
                "fault_phenomenon": "无法启动",
                "vehicle_location": "朝阳区建国路"
            }
        }

        status_code, response, duration = await self._public_request(
            "POST", "/api/autofill/record_fill_data",
            data=record_data
        )

        if status_code == 200 and response.get("code") == 200:
            data = response.get("data", {})
            record_id = data.get("id")
            print(f"  ✓ 记录创建成功")
            print(f"    - 记录ID: {record_id}")
            print(f"    - Session ID: {session_id}")
            self._add_result("填单记录-创建", True, status_code, response, duration_ms=duration)
            return True
        else:
            error_msg = response.get("msg", "Unknown error")
            print(f"  ✗ 记录创建失败: {error_msg}")
            self._add_result("填单记录-创建", False, status_code, response, error=error_msg, duration_ms=duration)
            return False

    # ==================== 运行所有测试 ====================
    async def run_all_tests(self):
        """运行所有测试步骤"""
        print("\n" + "="*60)
        print("400客服道路救援场景 - 完整测试")
        print("="*60)
        print(f"\n测试环境:")
        print(f"  - 后端地址: {self.base_url}")
        print(f"  - 租户ID: {self.context.tenant_id}")
        print(f"  - 应用名称: {self.context.app_name}")

        # 检查管理员Token
        if not self.admin_token:
            print("\n⚠️ 警告: 未设置ADMIN_TOKEN环境变量，管理接口可能无法访问")
            print("  请设置: export ADMIN_TOKEN=your_jwt_token")

        steps = [
            ("创建应用", self.step1_create_app),
            ("创建页面", self.step2_create_page),
            ("创建字段组", self.step3_create_field_group),
            ("创建字段明细", self.step4_create_field_specs),
            ("创建总结模板", self.step5_create_summary_template),
            ("测试公开接口-字段组", self.step6_test_public_field_group),
            ("测试公开接口-字段明细", self.step7_test_public_field_spec),
            ("测试LLM填单", self.step8_test_llm_fill),
            ("测试总结模板接口", self.step9_test_summary_template),
            ("测试填单记录接口", self.step10_test_record_fill_data),
        ]

        passed = 0
        failed = 0

        for step_name, step_func in steps:
            try:
                success = await step_func()
                if success:
                    passed += 1
                else:
                    failed += 1
                    # 关键步骤失败则停止
                    if step_name in ["创建应用", "创建页面", "创建字段组"]:
                        print(f"\n❌ 关键步骤'{step_name}'失败，停止测试")
                        break
            except Exception as e:
                print(f"\n❌ 步骤'{step_name}'发生异常: {e}")
                import traceback
                traceback.print_exc()
                failed += 1
                self._add_result(step_name, False, 0, None, error=str(e))

        # 打印测试报告
        self._print_report(passed, failed)

    def _print_report(self, passed: int, failed: int):
        """打印测试报告"""
        print("\n" + "="*60)
        print("测试报告")
        print("="*60)

        print(f"\n汇总:")
        print(f"  - 总步骤: {passed + failed}")
        print(f"  - 通过: {passed}")
        print(f"  - 失败: {failed}")

        print(f"\n详细结果:")
        for result in self.results:
            status = "✓" if result.success else "✗"
            print(f"  {status} {result.name}")
            if not result.success and result.error:
                print(f"    错误: {result.error}")

        # 保存测试上下文
        print(f"\n测试上下文:")
        print(f"  - 应用ID: {self.context.app_id}")
        print(f"  - API Key: {self.context.api_key}")
        print(f"  - 页面ID: {self.context.page_id}")
        print(f"  - 字段组ID: {self.context.field_group_id}")
        print(f"  - 字段组编码: {self.context.field_group_code}")
        print(f"  - 模板ID: {self.context.template_id}")

        print("\n" + "="*60)
        if failed == 0:
            print("✅ 所有测试通过!")
        else:
            print(f"⚠️  {failed} 个测试失败")
        print("="*60)


async def main():
    """主函数"""
    tester = RoadsideRescueScenarioTest()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
