#!/usr/bin/env python3
"""
400客服道路救援场景 - 公开接口测试脚本

此脚本仅测试公开接口功能，假设已通过管理后台配置好：
- 应用 (roadside_rescue)
- 页面 (rescue_workbench)
- 字段组 (道路救援服务记录)
- 字段明细 (14个字段)
- 总结模板

使用方法:
    # 先确保后端服务已启动
    python test_roadside_rescue_public_api.py

环境变量:
    BASE_URL: 后端服务地址 (默认: http://127.0.0.1:9999)
    API_KEY: 应用API Key (默认: 使用脚本中的测试值)
    FIELD_GROUP_ID: 字段组ID (默认: 1)
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
class TestResult:
    """测试结果"""
    name: str
    success: bool
    status_code: int
    response: Any
    error: Optional[str] = None
    duration_ms: float = 0


class RoadsideRescuePublicAPITest:
    """道路救援场景公开接口测试器"""

    def __init__(self):
        self.base_url = os.getenv("BASE_URL", "http://127.0.0.1:9999")
        # 默认API Key，实际使用时请替换
        self.api_key = os.getenv("API_KEY", "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR")
        self.tenant_id = int(os.getenv("TENANT_ID", "1"))
        self.field_group_id = int(os.getenv("FIELD_GROUP_ID", "1"))

        # 公开接口Headers
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-Tenant-ID": str(self.tenant_id),
        }

        self.results: List[TestResult] = []

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> tuple[int, Any, float]:
        """发送HTTP请求"""
        import time

        # 确保endpoint以/api开头
        if not endpoint.startswith("/api"):
            endpoint = f"/api{endpoint}"

        url = f"{self.base_url}{endpoint}"
        start = time.time()

        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=self.headers, params=params, timeout=60)
            else:
                response = await client.post(url, headers=self.headers, json=data, timeout=60)

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

    # ==================== 步骤1: 查询字段组 ====================
    async def step1_query_field_group(self):
        """步骤1: 查询字段组配置"""
        self._print_step(1, "查询字段组配置")

        self._print_substep("查询所有字段组...")
        status_code, response, duration = await self._request(
            "POST", "/autofill/field_group",
            data={}
        )

        if status_code == 200 and response.get("code") == 200:
            data = response.get("data", [])
            print(f"  ✓ 成功获取 {len(data)} 个字段组")

            if data:
                for group in data:
                    print(f"    - ID: {group.get('id')}, 名称: {group.get('group_name')}, 编码: {group.get('group_code')}")

                # 检查配置的字段组ID是否存在于列表中
                configured_id = int(os.getenv("FIELD_GROUP_ID", "1"))
                found = False
                for group in data:
                    if group.get('id') == configured_id:
                        self.field_group_id = configured_id
                        found = True
                        break

                if not found:
                    # 如果配置的ID不存在，使用第一个
                    self.field_group_id = data[0].get('id')
                    print(f"\n  ⚠ 配置的字段组ID={configured_id}不存在，使用第一个字段组 ID={self.field_group_id}")
                else:
                    print(f"\n  将使用字段组 ID={self.field_group_id} 进行后续测试")

            self._add_result("查询字段组", True, status_code, response, duration_ms=duration)
            return True
        else:
            error_msg = response.get("msg", "Unknown error")
            print(f"  ✗ 查询失败: {error_msg}")
            self._add_result("查询字段组", False, status_code, response, error=error_msg, duration_ms=duration)
            return False

    # ==================== 步骤2: 查询字段明细 ====================
    async def step2_query_field_specs(self):
        """步骤2: 查询字段明细"""
        self._print_step(2, "查询字段明细")

        self._print_substep(f"查询字段组ID={self.field_group_id}的字段明细...")
        status_code, response, duration = await self._request(
            "POST", "/autofill/field_spec/list",
            data={"field_group_id": self.field_group_id}
        )

        if status_code == 200 and response.get("code") == 200:
            data = response.get("data", [])
            print(f"  ✓ 成功获取 {len(data)} 个字段")

            # 按类型统计
            select_count = sum(1 for f in data if f.get("field_type") == "select")
            text_count = sum(1 for f in data if f.get("field_type") == "text")
            print(f"\n  字段统计:")
            print(f"    - select类型: {select_count} 个")
            print(f"    - text类型: {text_count} 个")

            # 显示字段列表
            print(f"\n  字段列表:")
            for field in data:
                status = "启用" if field.get("is_active") else "禁用"
                print(f"    - {field.get('field_name')}: {field.get('field_label')} ({field.get('field_type')}) [{status}]")

            self._add_result("查询字段明细", True, status_code, response, duration_ms=duration)
            return True
        else:
            error_msg = response.get("msg", "Unknown error")
            print(f"  ✗ 查询失败: {error_msg}")
            self._add_result("查询字段明细", False, status_code, response, error=error_msg, duration_ms=duration)
            return False

    # ==================== 步骤3: 测试LLM填单 ====================
    async def step3_test_llm_fill(self):
        """步骤3: 测试LLM填单功能"""
        self._print_step(3, "测试LLM填单功能")

        # 测试用例 - 模拟真实的400客服对话
        test_cases = [
            {
                "name": "标准道路救援请求",
                "query": """你好，我是张先生，我的车在朝阳区建国路这边抛锚了，无法启动。
我是车主本人，我的电话是13800138000，车架号是LSVAG2180E2100001，车型是奥迪A6。
车上就我一个人，车停在路边，不影响交通。我需要立即救援，拖到4S店去维修。"""
            },
            {
                "name": "家人代打电话-事故场景",
                "query": """喂，我帮我老公打电话，他的车在高速上发生事故了。
他姓李，电话是13912345678，车型是宝马X5，车架号WBAKB210X0F123456。
现在车停在应急车道上，比较安全，不影响其他车辆。车上有3个人。
希望能尽快救援，拖到最近的4S店。"""
            },
            {
                "name": "电瓶亏电-简单场景",
                "query": """您好，我的车电瓶没电了，需要搭电。
我姓王，电话是13700137000。车是奔驰C200，车架号是WDDWF4CB3JR123456，
在朝阳区三里屯这边。车停在停车场里，很安全。希望马上来人处理。"""
            },
            {
                "name": "复杂场景-爆胎+指定地址",
                "query": """你好，我的车爆胎了，需要救援。我是车主陈女士，
电话是13600136000，备用电话是13600136001。车是保时捷卡宴，
车架号是WP1AA2A20BLA12345，在海淀区中关村大街这边。
车停在路边，有点影响交通，车上有2个人。希望能尽快来，
拖到我家去，地址是海淀区某某小区。"""
            }
        ]

        all_success = True
        for test_case in test_cases:
            print(f"\n{'─'*50}")
            print(f"测试用例: {test_case['name']}")
            print('─'*50)
            print(f"输入对话:\n{test_case['query']}\n")

            status_code, response, duration = await self._request(
                "POST", "/autofill/llm/fill",
                data={
                    "field_group_id": self.field_group_id,
                    "input_data": {"query": test_case["query"]}
                }
            )

            if status_code == 200 and response.get("code") == 200:
                data = response.get("data", {})
                result = data.get("result", {})
                meta = data.get("_meta", {})

                print(f"✓ 填单成功")
                print(f"\n提取结果:")

                # 显示关键字段
                key_fields = [
                    ("customer_name", "客户姓名"),
                    ("caller_relation", "来电人身份"),
                    ("contact_phone", "联系电话"),
                    ("vehicle_system", "车系"),
                    ("vin_code", "VIN码"),
                    ("fault_phenomenon", "故障现象"),
                    ("vehicle_location", "车辆位置"),
                    ("is_parked_safely", "是否安全停放"),
                    ("is_affecting_traffic", "是否影响交通"),
                    ("passenger_count", "车上人数"),
                    ("expected_rescue_time", "期望救援时间"),
                    ("tow_destination", "拖车目的地"),
                ]

                for field_key, field_label in key_fields:
                    value = result.get(field_key, "")
                    if value:
                        print(f"  • {field_label}: {value}")

                # 显示元信息
                if meta:
                    print(f"\n元信息:")
                    print(f"  • 模型: {meta.get('model', 'unknown')}")
                    print(f"  • 耗时: {meta.get('latency_ms', 0)}ms")

                # 渲染并显示服务记录模板
                service_record = self._render_service_template(result)
                print(f"\n生成服务记录:")
                print(f"  {service_record}")

                self._add_result(f"LLM填单-{test_case['name']}", True, status_code, response, duration_ms=duration)
            else:
                error_msg = response.get("msg", "Unknown error")
                print(f"✗ 填单失败: {error_msg}")
                self._add_result(f"LLM填单-{test_case['name']}", False, status_code, response, error=error_msg, duration_ms=duration)
                all_success = False

        return all_success

    def _render_service_template(self, data: Dict[str, str]) -> str:
        """渲染服务记录模板"""
        from string import Template
        template_str = """车主${customer_name}（${caller_relation}）${contact_phone}请求道路救援。
车系：${vehicle_system}，车架号：${vin_code}。
车辆故障现象：${fault_phenomenon}。
车辆当前位置：${vehicle_location}。
是否安全停放：${is_parked_safely}，是否影响交通：${is_affecting_traffic}。
车上人数：${passenger_count}人。
客户联系电话：${contact_phone}（备用电话：${backup_phone}）。
期望救援时间：${expected_rescue_time}。
拖车目的地：${tow_destination}。
已告知客户预计到达时间并安排救援。"""

        # 处理空值，将空字符串替换为"未提供"
        safe_data = {k: (v if v else "未提供") for k, v in data.items()}
        template = Template(template_str)
        return template.safe_substitute(safe_data)

    # ==================== 步骤4: 测试总结模板接口 ====================
    async def step4_test_summary_template(self):
        """步骤4: 测试总结模板接口"""
        self._print_step(4, "测试总结模板接口")

        self._print_substep("查询模板列表...")
        status_code, response, duration = await self._request(
            "POST", "/autofill/summary_template/list",
            data={}
        )

        if status_code == 200 and response.get("code") == 200:
            data = response.get("data", [])
            print(f"  ✓ 成功获取 {len(data)} 个模板")
            for template in data:
                print(f"    - ID: {template.get('id')}, 名称: {template.get('name')}, 分类: {template.get('class_name')}")
            self._add_result("模板接口-列表", True, status_code, response, duration_ms=duration)

            # 如果有模板，查询详情
            if data:
                template_id = data[0].get('id')
                self._print_substep(f"查询模板详情 (ID={template_id})...")
                status_code, response, duration = await self._request(
                    "POST", "/autofill/summary_template",
                    data={"id": template_id}
                )

                if status_code == 200 and response.get("code") == 200:
                    data = response.get("data", {})
                    print(f"  ✓ 成功获取模板详情")
                    print(f"    - 名称: {data.get('name')}")
                    print(f"    - 分类: {data.get('class_name')}")
                    print(f"    - 内容预览: {data.get('template_content', '')[:100]}...")
                    self._add_result("模板接口-详情", True, status_code, response, duration_ms=duration)
                else:
                    error_msg = response.get("msg", "Unknown error")
                    print(f"  ✗ 查询失败: {error_msg}")
                    self._add_result("模板接口-详情", False, status_code, response, error=error_msg, duration_ms=duration)

            return True
        else:
            error_msg = response.get("msg", "Unknown error")
            print(f"  ✗ 查询失败: {error_msg}")
            self._add_result("模板接口-列表", False, status_code, response, error=error_msg, duration_ms=duration)
            return False

    # ==================== 步骤5: 测试填单记录接口 ====================
    async def step5_test_record_fill_data(self):
        """步骤5: 测试填单记录接口"""
        self._print_step(5, "测试填单记录接口")

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

        status_code, response, duration = await self._request(
            "POST", "/autofill/record_fill_data",
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

    # ==================== 步骤6: 测试下拉选项接口 ====================
    async def step6_test_dropdown_options(self):
        """步骤6: 测试下拉选项接口"""
        self._print_step(6, "测试下拉选项接口")

        self._print_substep("查询下拉选项列表...")
        status_code, response, duration = await self._request(
            "POST", "/autofill/dropdown_options/list",
            data={}
        )

        if status_code == 200 and response.get("code") == 200:
            data = response.get("data", [])
            print(f"  ✓ 成功获取 {len(data)} 个下拉选项")
            for option in data[:5]:  # 只显示前5个
                print(f"    - ID: {option.get('id')}, 值: {option.get('option_value')}")
            if len(data) > 5:
                print(f"    ... 还有 {len(data) - 5} 个选项")
            self._add_result("下拉选项-列表", True, status_code, response, duration_ms=duration)
            return True
        else:
            error_msg = response.get("msg", "Unknown error")
            print(f"  ✗ 查询失败: {error_msg}")
            self._add_result("下拉选项-列表", False, status_code, response, error=error_msg, duration_ms=duration)
            return False

    # ==================== 运行所有测试 ====================
    async def run_all_tests(self):
        """运行所有测试步骤"""
        print("\n" + "="*60)
        print("400客服道路救援场景 - 公开接口测试")
        print("="*60)
        print(f"\n测试环境:")
        print(f"  - 后端地址: {self.base_url}")
        print(f"  - API Key: {self.api_key[:20]}...")
        print(f"  - 租户ID: {self.tenant_id}")
        print(f"  - 字段组ID: {self.field_group_id}")

        steps = [
            ("查询字段组", self.step1_query_field_group),
            ("查询字段明细", self.step2_query_field_specs),
            ("测试LLM填单", self.step3_test_llm_fill),
            ("测试总结模板接口", self.step4_test_summary_template),
            ("测试填单记录接口", self.step5_test_record_fill_data),
            ("测试下拉选项接口", self.step6_test_dropdown_options),
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

        print("\n" + "="*60)
        if failed == 0:
            print("✅ 所有测试通过!")
        else:
            print(f"⚠️  {failed} 个测试失败")
        print("="*60)


async def main():
    """主函数"""
    tester = RoadsideRescuePublicAPITest()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
