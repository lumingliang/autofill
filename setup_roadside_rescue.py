#!/usr/bin/env python3
"""
400客服道路救援场景 - 完整配置脚本

此脚本用于创建完整的道路救援场景配置：
- 字段组：道路救援服务记录
- 字段明细：14个字段（业务类型、来电人身份、客户姓名、联系电话等）
- 总结模板：道路救援请求模板

使用方法:
    # 先确保后端服务已启动
    ADMIN_TOKEN="your_token" python setup_roadside_rescue.py

环境变量:
    BASE_URL: 后端服务地址 (默认: http://127.0.0.1:9999)
    ADMIN_TOKEN: 管理员JWT Token
    APP_NAME: 应用名称 (默认: test_app)
    PAGE_CODE: 页面编码 (默认: user_info_page)
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional

import httpx


class RoadsideRescueSetup:
    """道路救援场景配置器"""

    def __init__(self):
        self.base_url = os.getenv("BASE_URL", "http://127.0.0.1:9999")
        self.admin_token = os.getenv("ADMIN_TOKEN", "")
        self.app_name = os.getenv("APP_NAME", "test_app")
        self.page_code = os.getenv("PAGE_CODE", "user_info_page")
        self.tenant_id = int(os.getenv("TENANT_ID", "1"))

        if not self.admin_token:
            print("❌ 错误: 请设置 ADMIN_TOKEN 环境变量")
            print("   获取方法: curl -X POST http://127.0.0.1:9999/api/v1/base/access_token \\")
            print("     -H 'Content-Type: application/json' \\")
            print("     -d '{\"username\": \"admin\", \"password\": \"123456\"}'")
            sys.exit(1)

        self.headers = {
            "Content-Type": "application/json",
            "token": self.admin_token,
        }

        self.field_group_id: Optional[int] = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> tuple[int, Any]:
        """发送HTTP请求"""
        # 确保endpoint以/api/v1开头
        if not endpoint.startswith("/api/v1"):
            endpoint = f"/api/v1{endpoint}"

        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=self.headers, params=params, timeout=30)
            else:
                response = await client.post(url, headers=self.headers, json=data, timeout=30)

        try:
            resp_data = response.json()
        except:
            resp_data = response.text

        return response.status_code, resp_data

    async def get_page_id(self) -> Optional[int]:
        """获取页面ID"""
        print("\n📋 步骤1: 获取页面信息")

        status_code, response = await self._request(
            "GET", f"/autofill/page/list?page_size=100"
        )

        if status_code == 200 and response.get("code") == 200:
            pages = response.get("data", [])
            for page in pages:
                if page.get("page_code") == self.page_code:
                    print(f"   ✓ 找到页面: {page.get('page_name')} (ID: {page.get('id')})")
                    return page.get("id")

        print(f"   ✗ 未找到页面: {self.page_code}")
        return None

    async def create_field_group(self, page_id: int) -> Optional[int]:
        """创建字段组"""
        print("\n📋 步骤2: 创建字段组")

        # 检查是否已存在
        status_code, response = await self._request(
            "GET", f"/autofill/field_group/list?page_size=100"
        )

        if status_code == 200 and response.get("code") == 200:
            groups = response.get("data", [])
            for group in groups:
                if group.get("group_code") == "roadside_rescue_service":
                    print(f"   ✓ 字段组已存在: {group.get('group_name')} (ID: {group.get('id')})")
                    return group.get("id")

        # 创建字段组
        prompt_template = """你是一个专业的400客服道路救援智能填单助手。

请根据以下对话内容，提取道路救援相关的信息。

需要提取的字段：
{{fields_instructions}}

对话内容：
{{query}}

请严格按照字段要求提取信息，并以JSON格式返回结果。注意：
1. 如果信息未提供，返回空字符串
2. 对于选择型字段，必须从可选值中选择一个
3. 对于文本型字段，提取最准确的信息"""

        output_templates = {
            "service_record": {
                "template": "车主${customer_name}（${caller_relation}）${contact_phone}请求道路救援。车系：${vehicle_system}，车架号：${vin_code}。车辆故障现象：${fault_phenomenon}。车辆当前位置：${vehicle_location}。是否安全停放：${is_parked_safely}，是否影响交通：${is_affecting_traffic}。车上人数：${passenger_count}人。客户联系电话：${contact_phone}（备用电话：${backup_phone}）。期望救援时间：${expected_rescue_time}。拖车目的地：${tow_destination}。已告知客户预计到达时间并安排救援。",
                "description": "道路救援服务记录标准模板"
            }
        }

        data = {
            "app_name": self.app_name,
            "page_id": page_id,
            "group_name": "道路救援服务记录",
            "group_code": "roadside_rescue_service",
            "prompt_template_base": prompt_template,
            "output_templates": output_templates,
            "description": "400客服道路救援场景字段组，包含业务类型、来电人身份、客户信息、车辆信息、故障信息、救援需求等字段"
        }

        status_code, response = await self._request(
            "POST", "/autofill/field_group/create",
            data=data
        )

        if status_code == 200 and response.get("code") == 200:
            group_id = response.get("data", {}).get("id")
            print(f"   ✓ 字段组创建成功 (ID: {group_id})")
            return group_id
        else:
            print(f"   ✗ 创建失败: {response.get('msg', 'Unknown error')}")
            return None

    async def create_field_specs(self, field_group_id: int) -> bool:
        """创建字段明细"""
        print("\n📋 步骤3: 创建字段明细")

        # 先检查现有字段
        status_code, response = await self._request(
            "GET", f"/autofill/field_spec/list?field_group_id={field_group_id}&page_size=100"
        )

        existing_count = 0
        if status_code == 200 and response.get("code") == 200:
            existing_count = len(response.get("data", []))
            if existing_count > 0:
                print(f"   ℹ 字段组已有 {existing_count} 个字段，将创建新字段")

        # 定义14个字段
        fields = [
            # 1. 业务类型
            {
                "field_name": "business_type",
                "field_label": "业务类型",
                "field_type": "select",
                "fill_instruction": "根据对话内容判断业务类型",
                "options": {
                    "items": [
                        {"value": "道路救援", "label": "道路救援", "base_annotation": "车辆故障、事故等需要救援", "corrections": []},
                        {"value": "业务咨询", "label": "业务咨询", "base_annotation": "产品咨询、服务咨询等", "corrections": []},
                        {"value": "投诉建议", "label": "投诉建议", "base_annotation": "客户投诉或建议", "corrections": []}
                    ]
                }
            },
            # 2. 来电人身份
            {
                "field_name": "caller_relation",
                "field_label": "来电人身份",
                "field_type": "select",
                "fill_instruction": "判断来电人与车主的关系",
                "options": {
                    "items": [
                        {"value": "本人", "label": "本人", "base_annotation": "车主本人来电", "corrections": []},
                        {"value": "家人", "label": "家人", "base_annotation": "车主家人代打电话", "corrections": []},
                        {"value": "朋友", "label": "朋友", "base_annotation": "车主朋友代打电话", "corrections": []},
                        {"value": "同事", "label": "同事", "base_annotation": "车主同事代打电话", "corrections": []},
                        {"value": "其他", "label": "其他", "base_annotation": "其他关系", "corrections": []}
                    ]
                }
            },
            # 3. 客户姓名
            {
                "field_name": "customer_name",
                "field_label": "客户姓名",
                "field_type": "text",
                "fill_instruction": "提取客户姓名，如张先生、李女士等",
                "options": None
            },
            # 4. 联系电话
            {
                "field_name": "contact_phone",
                "field_label": "联系电话",
                "field_type": "text",
                "fill_instruction": "提取客户联系电话，11位手机号码",
                "options": None
            },
            # 5. 备用电话
            {
                "field_name": "backup_phone",
                "field_label": "备用电话",
                "field_type": "text",
                "fill_instruction": "提取备用联系电话，如未提供则留空",
                "options": None
            },
            # 6. 车系
            {
                "field_name": "vehicle_system",
                "field_label": "车系",
                "field_type": "text",
                "fill_instruction": "提取车辆品牌和型号，如奥迪A6、宝马X5等",
                "options": None
            },
            # 7. 车架号(VIN)
            {
                "field_name": "vin_code",
                "field_label": "车架号(VIN)",
                "field_type": "text",
                "fill_instruction": "提取17位车辆识别代号(VIN码)",
                "options": None
            },
            # 8. 故障现象
            {
                "field_name": "fault_phenomenon",
                "field_label": "故障现象",
                "field_type": "select",
                "fill_instruction": "根据描述判断故障类型",
                "options": {
                    "items": [
                        {"value": "无法启动", "label": "无法启动", "base_annotation": "车辆无法启动，电瓶亏电或机械故障", "corrections": []},
                        {"value": "事故", "label": "事故", "base_annotation": "车辆发生碰撞事故", "corrections": []},
                        {"value": "爆胎", "label": "爆胎", "base_annotation": "轮胎爆胎需要更换", "corrections": []},
                        {"value": "缺油", "label": "缺油", "base_annotation": "车辆燃油耗尽", "corrections": []},
                        {"value": "搭电", "label": "搭电", "base_annotation": "电瓶亏电需要搭电", "corrections": []},
                        {"value": "其他", "label": "其他", "base_annotation": "其他故障类型", "corrections": []}
                    ]
                }
            },
            # 9. 车辆位置
            {
                "field_name": "vehicle_location",
                "field_label": "车辆位置",
                "field_type": "text",
                "fill_instruction": "提取车辆当前所在详细地址",
                "options": None
            },
            # 10. 是否安全停放
            {
                "field_name": "is_parked_safely",
                "field_label": "是否安全停放",
                "field_type": "select",
                "fill_instruction": "判断车辆是否停放在安全位置",
                "options": {
                    "items": [
                        {"value": "是", "label": "是", "base_annotation": "车辆停放在安全位置", "corrections": []},
                        {"value": "否", "label": "否", "base_annotation": "车辆未停放在安全位置", "corrections": []}
                    ]
                }
            },
            # 11. 是否影响交通
            {
                "field_name": "is_affecting_traffic",
                "field_label": "是否影响交通",
                "field_type": "select",
                "fill_instruction": "判断车辆是否影响其他车辆通行",
                "options": {
                    "items": [
                        {"value": "是", "label": "是", "base_annotation": "车辆影响交通", "corrections": []},
                        {"value": "否", "label": "否", "base_annotation": "车辆不影响交通", "corrections": []}
                    ]
                }
            },
            # 12. 车上人数
            {
                "field_name": "passenger_count",
                "field_label": "车上人数",
                "field_type": "text",
                "fill_instruction": "提取车上人员数量",
                "options": None
            },
            # 13. 期望救援时间
            {
                "field_name": "expected_rescue_time",
                "field_label": "期望救援时间",
                "field_type": "select",
                "fill_instruction": "判断客户期望的救援时间",
                "options": {
                    "items": [
                        {"value": "立即", "label": "立即", "base_annotation": "客户要求立即救援", "corrections": []},
                        {"value": "预约时间", "label": "预约时间", "base_annotation": "客户希望预约特定时间", "corrections": []}
                    ]
                }
            },
            # 14. 拖车目的地
            {
                "field_name": "tow_destination",
                "field_label": "拖车目的地",
                "field_type": "select",
                "fill_instruction": "判断客户希望的拖车目的地",
                "options": {
                    "items": [
                        {"value": "4S店", "label": "4S店", "base_annotation": "拖至4S店维修", "corrections": []},
                        {"value": "指定地址", "label": "指定地址", "base_annotation": "拖至客户指定地址", "corrections": []}
                    ]
                }
            }
        ]

        success_count = 0
        for field in fields:
            data = {
                "field_group_id": field_group_id,
                **field
            }

            status_code, response = await self._request(
                "POST", "/autofill/field_spec/create",
                data=data
            )

            if status_code == 200 and response.get("code") == 200:
                success_count += 1
                print(f"   ✓ {field['field_label']}")
            else:
                print(f"   ✗ {field['field_label']}: {response.get('msg', 'Unknown error')}")

        print(f"\n   总计: {success_count}/{len(fields)} 个字段创建成功")
        return success_count == len(fields)

    async def create_summary_template(self) -> bool:
        """创建总结模板"""
        print("\n📋 步骤4: 创建总结模板")

        # 检查是否已存在
        status_code, response = await self._request(
            "POST", "/autofill/summary_template/list",
            data={}
        )

        if status_code == 200 and response.get("code") == 200:
            templates = response.get("data", [])
            for template in templates:
                if template.get("name") == "道路救援请求":
                    print(f"   ✓ 模板已存在: {template.get('name')} (ID: {template.get('id')})")
                    return True

        # 创建模板
        template_content = """车主${customer_name}（${caller_relation}）${contact_phone}请求道路救援。
车系：${vehicle_system}，车架号：${vin_code}。
车辆故障现象：${fault_phenomenon}。
车辆当前位置：${vehicle_location}。
是否安全停放：${is_parked_safely}，是否影响交通：${is_affecting_traffic}。
车上人数：${passenger_count}人。
客户联系电话：${contact_phone}（备用电话：${backup_phone}）。
期望救援时间：${expected_rescue_time}。
拖车目的地：${tow_destination}。
已告知客户预计到达时间并安排救援。"""

        data = {
            "app_name": self.app_name,
            "name": "道路救援请求",
            "summary": "道路救援服务记录标准模板",
            "class_name": "救援服务",
            "template_content": template_content
        }

        status_code, response = await self._request(
            "POST", "/autofill/summary_template/create",
            data=data
        )

        if status_code == 200 and response.get("code") == 200:
            template_id = response.get("data", {}).get("id")
            print(f"   ✓ 模板创建成功 (ID: {template_id})")
            return True
        else:
            print(f"   ✗ 创建失败: {response.get('msg', 'Unknown error')}")
            return False

    async def run(self):
        """运行配置"""
        print("="*60)
        print("400客服道路救援场景 - 配置脚本")
        print("="*60)
        print(f"\n配置信息:")
        print(f"  - 后端地址: {self.base_url}")
        print(f"  - 应用名称: {self.app_name}")
        print(f"  - 页面编码: {self.page_code}")
        print(f"  - 租户ID: {self.tenant_id}")

        # 获取页面ID
        page_id = await self.get_page_id()
        if not page_id:
            print("\n❌ 配置失败: 无法获取页面ID")
            return False

        # 创建字段组
        field_group_id = await self.create_field_group(page_id)
        if not field_group_id:
            print("\n❌ 配置失败: 无法创建字段组")
            return False

        self.field_group_id = field_group_id

        # 创建字段明细
        if not await self.create_field_specs(field_group_id):
            print("\n⚠ 字段创建部分失败")

        # 创建总结模板
        await self.create_summary_template()

        print("\n" + "="*60)
        print("✅ 配置完成!")
        print("="*60)
        print(f"\n字段组ID: {self.field_group_id}")
        print(f"\n接下来可以运行测试脚本:")
        print(f"  API_KEY=af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR FIELD_GROUP_ID={self.field_group_id} python test_roadside_rescue_public_api.py")

        return True


async def main():
    setup = RoadsideRescueSetup()
    success = await setup.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
