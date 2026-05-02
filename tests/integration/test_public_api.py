#!/usr/bin/env python3
"""
智能填单系统公共接口测试脚本
一键测试所有公共接口

使用方法:
    python test_public_api.py

环境变量:
    API_KEY: API密钥 (默认: af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR)
    TENANT_ID: 租户ID (默认: 1)
    BASE_URL: 基础URL (默认: http://127.0.0.1:9999)
"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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


class PublicAPITester:
    """公共接口测试器"""

    def __init__(self):
        self.api_key = os.getenv("API_KEY", "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR")
        self.tenant_id = os.getenv("TENANT_ID", "1")
        self.base_url = os.getenv("BASE_URL", "http://127.0.0.1:9999")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-Tenant-ID": self.tenant_id,
        }
        self.results: List[TestResult] = []

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> tuple[int, Any, float]:
        """发送HTTP请求"""
        import time

        url = f"{self.base_url}{endpoint}"
        start = time.time()

        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=self.headers, params=params)
            else:
                response = await client.post(url, headers=self.headers, json=data)

        duration = (time.time() - start) * 1000
        return response.status_code, response.json(), duration

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

    async def test_field_group_list(self):
        """测试字段组列表接口"""
        name = "字段组列表 (/api/autofill/field_group)"
        try:
            status_code, response, duration = await self._make_request(
                "POST", "/api/autofill/field_group", data={"page_id": 1}
            )

            if status_code == 200 and response.get("code") == 200:
                data = response.get("data", [])
                self._add_result(
                    name, True, status_code, response,
                    duration_ms=duration
                )
                print(f"  ✓ 成功获取 {len(data)} 个字段组")
            else:
                self._add_result(
                    name, False, status_code, response,
                    error=response.get("msg", "Unknown error"),
                    duration_ms=duration
                )
                print(f"  ✗ 失败: {response.get('msg')}")
        except Exception as e:
            self._add_result(name, False, 0, None, error=str(e))
            print(f"  ✗ 异常: {e}")

    async def test_field_spec_list(self):
        """测试字段明细列表接口"""
        name = "字段明细列表 (/api/autofill/field_spec/list)"
        try:
            status_code, response, duration = await self._make_request(
                "POST", "/api/autofill/field_spec/list", data={"field_group_id": 1}
            )

            if status_code == 200 and response.get("code") == 200:
                data = response.get("data", [])
                self._add_result(
                    name, True, status_code, response,
                    duration_ms=duration
                )
                print(f"  ✓ 成功获取 {len(data)} 个字段")
                for field in data:
                    print(f"    - {field['field_name']} ({field['field_label']}): {'启用' if field['is_active'] else '禁用'}")
            else:
                self._add_result(
                    name, False, status_code, response,
                    error=response.get("msg", "Unknown error"),
                    duration_ms=duration
                )
                print(f"  ✗ 失败: {response.get('msg')}")
        except Exception as e:
            self._add_result(name, False, 0, None, error=str(e))
            print(f"  ✗ 异常: {e}")

    async def test_llm_fill(self):
        """测试LLM填单接口"""
        name = "LLM填单 (/api/autofill/llm/fill)"
        test_queries = [
            {
                "desc": "标准测试",
                "query": "你好，我叫张三，我的手机号是13800138000，我的车架号是LSVAG2180E2100001"
            },
            {
                "desc": "中文姓名+手机",
                "query": "我是李四，电话是13912345678"
            },
            {
                "desc": "只有VIN码",
                "query": "我的车架号码是WBAKB210X0F123456"
            }
        ]

        for test in test_queries:
            test_name = f"{name} - {test['desc']}"
            print(f"\n  测试: {test['desc']}")
            print(f"  输入: {test['query']}")

            try:
                status_code, response, duration = await self._make_request(
                    "POST",
                    "/api/autofill/llm/fill",
                    data={
                        "field_group_id": 1,
                        "input_data": {"query": test["query"]}
                    }
                )

                if status_code == 200 and response.get("code") == 200:
                    result = response.get("data", {}).get("result", {})
                    meta = response.get("data", {}).get("_meta", {})

                    if result:
                        self._add_result(
                            test_name, True, status_code, response,
                            duration_ms=duration
                        )
                        print(f"  ✓ 成功提取字段:")
                        for k, v in result.items():
                            print(f"    - {k}: {v}")
                        print(f"    模型: {meta.get('model')}")
                        print(f"    耗时: {meta.get('latency_ms')}ms")
                    else:
                        self._add_result(
                            test_name, False, status_code, response,
                            error="返回结果为空",
                            duration_ms=duration
                        )
                        print(f"  ✗ 返回结果为空")
                else:
                    self._add_result(
                        test_name, False, status_code, response,
                        error=response.get("msg", "Unknown error"),
                        duration_ms=duration
                    )
                    print(f"  ✗ 失败: {response.get('msg')}")
            except Exception as e:
                self._add_result(test_name, False, 0, None, error=str(e))
                print(f"  ✗ 异常: {e}")

    async def test_summary_template_list(self):
        """测试总结模板列表接口"""
        name = "总结模板列表 (/api/autofill/summary_template/list)"
        try:
            status_code, response, duration = await self._make_request(
                "POST", "/api/autofill/summary_template/list", data={}
            )

            if status_code == 200 and response.get("code") == 200:
                data = response.get("data", [])
                self._add_result(
                    name, True, status_code, response,
                    duration_ms=duration
                )
                print(f"  ✓ 成功获取 {len(data)} 个模板")
            else:
                self._add_result(
                    name, False, status_code, response,
                    error=response.get("msg", "Unknown error"),
                    duration_ms=duration
                )
                print(f"  ✗ 失败: {response.get('msg')}")
        except Exception as e:
            self._add_result(name, False, 0, None, error=str(e))
            print(f"  ✗ 异常: {e}")

    async def test_dropdown_options_list(self):
        """测试下拉选项列表接口"""
        name = "下拉选项列表 (/api/autofill/dropdown_options/list)"
        try:
            status_code, response, duration = await self._make_request(
                "POST", "/api/autofill/dropdown_options/list", data={}
            )

            if status_code == 200 and response.get("code") == 200:
                data = response.get("data", [])
                self._add_result(
                    name, True, status_code, response,
                    duration_ms=duration
                )
                print(f"  ✓ 成功获取 {len(data)} 个下拉选项")
            else:
                self._add_result(
                    name, False, status_code, response,
                    error=response.get("msg", "Unknown error"),
                    duration_ms=duration
                )
                print(f"  ✗ 失败: {response.get('msg')}")
        except Exception as e:
            self._add_result(name, False, 0, None, error=str(e))
            print(f"  ✗ 异常: {e}")

    async def test_field_spec_update(self):
        """测试字段更新接口 - 复杂场景测试"""
        name_base = "字段更新 (/api/autofill/field_spec/update)"

        # 首先获取字段列表
        print("\n  步骤1: 获取当前字段列表...")
        try:
            status_code, response, _ = await self._make_request(
                "POST", "/api/autofill/field_spec/list", data={"field_group_id": 1}
            )

            if status_code != 200 or response.get("code") != 200:
                self._add_result(
                    f"{name_base} - 获取字段列表", False, status_code, response,
                    error="无法获取字段列表"
                )
                print(f"  ✗ 无法获取字段列表")
                return

            fields = response.get("data", [])
            if not fields:
                self._add_result(
                    f"{name_base} - 获取字段列表", False, status_code, response,
                    error="字段列表为空"
                )
                print(f"  ✗ 字段列表为空")
                return

            print(f"  ✓ 获取到 {len(fields)} 个字段")

            # 选择第一个字段进行测试
            test_field = fields[0]
            field_id = test_field["id"]
            original_label = test_field["field_label"]
            original_instruction = test_field.get("fill_instruction", "")
            original_active = test_field["is_active"]

            print(f"\n  步骤2: 测试更新字段标签和提取指令...")
            print(f"  目标字段: {test_field['field_name']} (ID: {field_id})")

            # 测试场景1: 更新字段标签和提取指令
            new_label = f"{original_label}_测试"
            new_instruction = f"{original_instruction}_测试指令"

            status_code, response, duration = await self._make_request(
                "POST",
                "/api/autofill/field_spec/update",
                data={
                    "field_group_id": 1,
                    "fields": [
                        {
                            "id": field_id,
                            "field_label": new_label,
                            "fill_instruction": new_instruction
                        }
                    ]
                }
            )

            if status_code == 200 and response.get("code") == 200:
                updated_count = response.get("data", {}).get("updated_count", 0)
                if updated_count > 0:
                    self._add_result(
                        f"{name_base} - 更新标签和指令", True, status_code, response,
                        duration_ms=duration
                    )
                    print(f"  ✓ 成功更新字段标签和指令")
                    print(f"    新标签: {new_label}")
                    print(f"    新指令: {new_instruction}")
                else:
                    self._add_result(
                        f"{name_base} - 更新标签和指令", False, status_code, response,
                        error="未更新任何字段",
                        duration_ms=duration
                    )
                    print(f"  ✗ 未更新任何字段")
            else:
                self._add_result(
                    f"{name_base} - 更新标签和指令", False, status_code, response,
                    error=response.get("msg", "Unknown error"),
                    duration_ms=duration
                )
                print(f"  ✗ 失败: {response.get('msg')}")

            # 测试场景2: 禁用字段
            print(f"\n  步骤3: 测试禁用字段...")
            status_code, response, duration = await self._make_request(
                "POST",
                "/api/autofill/field_spec/update",
                data={
                    "field_group_id": 1,
                    "fields": [
                        {
                            "id": field_id,
                            "is_active": False
                        }
                    ]
                }
            )

            if status_code == 200 and response.get("code") == 200:
                updated_count = response.get("data", {}).get("updated_count", 0)
                if updated_count > 0:
                    self._add_result(
                        f"{name_base} - 禁用字段", True, status_code, response,
                        duration_ms=duration
                    )
                    print(f"  ✓ 成功禁用字段")
                else:
                    self._add_result(
                        f"{name_base} - 禁用字段", False, status_code, response,
                        error="未更新任何字段",
                        duration_ms=duration
                    )
                    print(f"  ✗ 未更新任何字段")
            else:
                self._add_result(
                    f"{name_base} - 禁用字段", False, status_code, response,
                    error=response.get("msg", "Unknown error"),
                    duration_ms=duration
                )
                print(f"  ✗ 失败: {response.get('msg')}")

            # 测试场景3: 批量更新多个字段
            print(f"\n  步骤4: 测试批量更新多个字段...")
            if len(fields) >= 2:
                batch_updates = []
                for i, field in enumerate(fields[:2]):  # 只更新前两个字段
                    batch_updates.append({
                        "id": field["id"],
                        "field_label": f"{field['field_label']}_批量测试"
                    })

                status_code, response, duration = await self._make_request(
                    "POST",
                    "/api/autofill/field_spec/update",
                    data={
                        "field_group_id": 1,
                        "fields": batch_updates
                    }
                )

                if status_code == 200 and response.get("code") == 200:
                    updated_count = response.get("data", {}).get("updated_count", 0)
                    if updated_count == len(batch_updates):
                        self._add_result(
                            f"{name_base} - 批量更新", True, status_code, response,
                            duration_ms=duration
                        )
                        print(f"  ✓ 成功批量更新 {updated_count} 个字段")
                    else:
                        self._add_result(
                            f"{name_base} - 批量更新", False, status_code, response,
                            error=f"期望更新 {len(batch_updates)} 个，实际更新 {updated_count} 个",
                            duration_ms=duration
                        )
                        print(f"  ✗ 批量更新不完整")
                else:
                    self._add_result(
                        f"{name_base} - 批量更新", False, status_code, response,
                        error=response.get("msg", "Unknown error"),
                        duration_ms=duration
                    )
                    print(f"  ✗ 失败: {response.get('msg')}")
            else:
                print(f"  ⚠ 字段数量不足，跳过批量更新测试")

            # 测试场景4: 恢复字段状态
            print(f"\n  步骤5: 恢复字段原始状态...")
            status_code, response, duration = await self._make_request(
                "POST",
                "/api/autofill/field_spec/update",
                data={
                    "field_group_id": 1,
                    "fields": [
                        {
                            "id": field_id,
                            "field_label": original_label,
                            "fill_instruction": original_instruction,
                            "is_active": original_active
                        }
                    ]
                }
            )

            if status_code == 200 and response.get("code") == 200:
                updated_count = response.get("data", {}).get("updated_count", 0)
                if updated_count > 0:
                    self._add_result(
                        f"{name_base} - 恢复原始状态", True, status_code, response,
                        duration_ms=duration
                    )
                    print(f"  ✓ 成功恢复字段原始状态")
                else:
                    self._add_result(
                        f"{name_base} - 恢复原始状态", False, status_code, response,
                        error="未更新任何字段",
                        duration_ms=duration
                    )
                    print(f"  ✗ 未更新任何字段")
            else:
                self._add_result(
                    f"{name_base} - 恢复原始状态", False, status_code, response,
                    error=response.get("msg", "Unknown error"),
                    duration_ms=duration
                )
                print(f"  ✗ 失败: {response.get('msg')}")

            # 测试场景5: 错误处理 - 更新不存在的字段
            print(f"\n  步骤6: 测试错误处理 - 更新不存在的字段...")
            status_code, response, duration = await self._make_request(
                "POST",
                "/api/autofill/field_spec/update",
                data={
                    "field_group_id": 1,
                    "fields": [
                        {
                            "id": 99999,  # 不存在的ID
                            "field_label": "测试"
                        }
                    ]
                }
            )

            if status_code == 200 and response.get("code") == 200:
                errors = response.get("data", {}).get("errors", [])
                if errors and len(errors) > 0:
                    self._add_result(
                        f"{name_base} - 错误处理", True, status_code, response,
                        duration_ms=duration
                    )
                    print(f"  ✓ 正确返回错误信息: {errors[0].get('error')}")
                else:
                    self._add_result(
                        f"{name_base} - 错误处理", False, status_code, response,
                        error="应该返回错误但未返回",
                        duration_ms=duration
                    )
                    print(f"  ✗ 应该返回错误但未返回")
            else:
                # 返回非200状态码也是可接受的错误处理方式
                self._add_result(
                    f"{name_base} - 错误处理", True, status_code, response,
                    duration_ms=duration
                )
                print(f"  ✓ 正确返回错误状态码: {status_code}")

        except Exception as e:
            self._add_result(name_base, False, 0, None, error=str(e))
            print(f"  ✗ 异常: {e}")

    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("智能填单系统公共接口测试")
        print("=" * 60)
        print(f"基础URL: {self.base_url}")
        print(f"租户ID: {self.tenant_id}")
        print(f"API Key: {self.api_key[:10]}...{self.api_key[-5:]}")
        print("=" * 60)

        # 测试字段组列表
        print("\n【1】测试字段组列表接口...")
        await self.test_field_group_list()

        # 测试字段明细列表
        print("\n【2】测试字段明细列表接口...")
        await self.test_field_spec_list()

        # 测试LLM填单
        print("\n【3】测试LLM填单接口...")
        await self.test_llm_fill()

        # 测试总结模板列表
        print("\n【4】测试总结模板列表接口...")
        await self.test_summary_template_list()

        # 测试下拉选项列表
        print("\n【5】测试下拉选项列表接口...")
        await self.test_dropdown_options_list()

        # 测试字段更新接口
        print("\n【6】测试字段更新接口（复杂场景）...")
        await self.test_field_spec_update()

        # 打印测试报告
        self._print_report()

    def _print_report(self):
        """打印测试报告"""
        print("\n" + "=" * 60)
        print("测试报告")
        print("=" * 60)

        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        failed = total - passed

        print(f"\n总计: {total} | 通过: {passed} | 失败: {failed}")
        print(f"成功率: {passed/total*100:.1f}%")

        if failed > 0:
            print("\n失败的测试:")
            for r in self.results:
                if not r.success:
                    print(f"  ✗ {r.name}")
                    if r.error:
                        print(f"    错误: {r.error}")

        print("\n详细结果:")
        for r in self.results:
            status = "✓" if r.success else "✗"
            duration = f"{r.duration_ms:.0f}ms" if r.duration_ms > 0 else "N/A"
            print(f"  {status} {r.name} ({duration})")

        print("=" * 60)

        # 返回退出码
        return 0 if failed == 0 else 1


def main():
    """主函数"""
    tester = PublicAPITester()

    try:
        asyncio.run(tester.run_all_tests())
    except KeyboardInterrupt:
        print("\n\n测试被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n测试出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
