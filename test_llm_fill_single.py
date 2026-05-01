#!/usr/bin/env python3
"""
LLM填单功能单独测试脚本

使用方法:
    python test_llm_fill_single.py

环境变量:
    BASE_URL: 后端服务地址 (默认: http://127.0.0.1:9999)
    API_KEY: 应用API Key (默认: af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR)
    FIELD_GROUP_ID: 字段组ID (默认: 1)
"""

import asyncio
import json
import os
import time
from typing import Any, Dict, Optional

import httpx


class LLMFillTester:
    """LLM填单功能测试器"""

    def __init__(self):
        self.base_url = os.getenv("BASE_URL", "http://127.0.0.1:9999")
        self.api_key = os.getenv("API_KEY", "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR")
        self.tenant_id = int(os.getenv("TENANT_ID", "1"))
        # 支持通过 ID 或 Code 指定字段组，Code 是更稳定的唯一标识
        self.field_group_id = os.getenv("FIELD_GROUP_ID")
        self.field_group_code = os.getenv("FIELD_GROUP_CODE", "roadside_rescue_service")

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-Tenant-ID": str(self.tenant_id),
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
    ) -> tuple[int, Any, float]:
        """发送HTTP请求"""
        if not endpoint.startswith("/api"):
            endpoint = f"/api{endpoint}"

        url = f"{self.base_url}{endpoint}"
        start = time.time()

        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=self.headers, timeout=60)
            else:
                response = await client.post(url, headers=self.headers, json=data, timeout=60)

        duration = (time.time() - start) * 1000

        try:
            resp_data = response.json()
        except:
            resp_data = response.text

        return response.status_code, resp_data, duration

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

        safe_data = {k: (v if v else "未提供") for k, v in data.items()}
        template = Template(template_str)
        return template.safe_substitute(safe_data)

    async def test_llm_fill(self, test_case: Dict[str, str]) -> bool:
        """测试LLM填单"""
        print(f"\n{'='*60}")
        print(f"测试用例: {test_case['name']}")
        print('='*60)
        print(f"输入对话:\n{test_case['query']}\n")

        # 优先使用 field_group_code（更稳定的唯一标识）
        if self.field_group_id:
            request_data = {
                "field_group_id": int(self.field_group_id),
                "input_data": {"query": test_case["query"]}
            }
        else:
            request_data = {
                "field_group_code": self.field_group_code,
                "input_data": {"query": test_case["query"]}
            }

        status_code, response, duration = await self._request(
            "POST", "/autofill/llm/fill",
            data=request_data
        )

        print(f"请求状态: {status_code}")
        print(f"响应时间: {duration:.2f}ms")

        if status_code == 200 and response.get("code") == 200:
            data = response.get("data", {})
            result = data.get("result", {})
            meta = data.get("_meta", {})

            print(f"\n✓ 填单成功")
            print(f"\n提取结果:")

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

            if meta:
                print(f"\n元信息:")
                print(f"  • 模型: {meta.get('model', 'unknown')}")
                print(f"  • 耗时: {meta.get('latency_ms', 0)}ms")

            service_record = self._render_service_template(result)
            print(f"\n生成服务记录:")
            print(f"  {service_record}")

            return True
        else:
            error_msg = response.get("msg", "Unknown error")
            print(f"\n✗ 填单失败: {error_msg}")
            print(f"完整响应: {json.dumps(response, indent=2, ensure_ascii=False)}")
            return False

    async def run_tests(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("LLM填单功能单独测试")
        print("="*60)
        print(f"\n测试环境:")
        print(f"  - 后端地址: {self.base_url}")
        print(f"  - API Key: {self.api_key}")
        print(f"  - 租户ID: {self.tenant_id}")
        if self.field_group_id:
            print(f"  - 字段组ID: {self.field_group_id}")
        else:
            print(f"  - 字段组Code: {self.field_group_code}")

        # 测试用例
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

        results = []
        for test_case in test_cases:
            success = await self.test_llm_fill(test_case)
            results.append((test_case["name"], success))

        # 打印总结
        print("\n" + "="*60)
        print("测试总结")
        print("="*60)
        for name, success in results:
            status = "✓ 通过" if success else "✗ 失败"
            print(f"  {status}: {name}")

        passed = sum(1 for _, s in results if s)
        print(f"\n总计: {passed}/{len(results)} 通过")


async def main():
    tester = LLMFillTester()
    await tester.run_tests()


if __name__ == "__main__":
    asyncio.run(main())
