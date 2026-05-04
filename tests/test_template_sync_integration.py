#!/usr/bin/env python3
"""
模板字段同步集成测试

测试完整的模板字段同步流程，包括:
1. 查询模板列表
2. 创建/更新"场景分类"字段
3. 为模板创建服务记录字段组
4. 验证创建结果

使用方法:
    python tests/test_template_sync_integration.py --api-key <your_api_key>

环境要求:
    - 服务器必须正在运行
    - 数据库中需要有测试数据（AppManagement, SummaryTemplate, FillPage）
"""

import asyncio
import argparse
import json
import sys
import os
from typing import Dict, List, Any

import httpx


# 默认配置
DEFAULT_BASE_URL = "http://localhost:9999"
DEFAULT_API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
DEFAULT_PAGE_NAME = "用户信息页"


class TemplateSyncIntegrationTest:
    """模板字段同步集成测试"""

    def __init__(self, base_url: str, api_key: str, page_name: str = DEFAULT_PAGE_NAME):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.page_name = page_name
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.test_results: List[Dict] = []

    async def make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """发送 HTTP 请求"""
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient() as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(url, headers=self.headers, params=params, timeout=30)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=self.headers, json=data, timeout=30)
                else:
                    raise ValueError(f"不支持的 HTTP 方法: {method}")

                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                return {
                    "error": True,
                    "status_code": e.response.status_code,
                    "detail": e.response.text
                }
            except Exception as e:
                return {"error": True, "detail": str(e)}

    def log(self, message: str, level: str = "info"):
        """打印日志"""
        prefix = {"info": "ℹ️", "success": "✅", "error": "❌", "warning": "⚠️"}.get(level, "ℹ️")
        print(f"{prefix} {message}")

    def record_result(self, test_name: str, success: bool, message: str = "", data: Any = None):
        """记录测试结果"""
        self.test_results.append({
            "test_name": test_name,
            "success": success,
            "message": message,
            "data": data
        })
        level = "success" if success else "error"
        self.log(f"{test_name}: {message}", level)

    # ==================== 测试场景1: 基础接口测试 ====================

    async def test_summary_template_list(self):
        """测试1: 查询模板列表"""
        self.log("\n【测试1】查询模板列表")

        result = await self.make_request("GET", "/api/autofill/summary_template/list")

        if result.get("code") == 200:
            templates = result.get("data", [])
            self.record_result(
                "查询模板列表",
                True,
                f"成功获取 {len(templates)} 个模板",
                {"template_count": len(templates), "first_template": templates[0] if templates else None}
            )
            return templates
        else:
            self.record_result("查询模板列表", False, f"失败: {result.get('detail', result)}")
            return []

    async def test_summary_template_detail(self, template_id: int):
        """测试2: 查询模板详情"""
        self.log(f"\n【测试2】查询模板详情 (ID: {template_id})")

        result = await self.make_request(
            "GET",
            "/api/autofill/summary_template",
            params={"id": template_id}
        )

        if result.get("code") == 200:
            data = result.get("data", {})
            self.record_result(
                "查询模板详情",
                True,
                f"成功获取模板: {data.get('name')}",
                {"template_name": data.get("name"), "has_content": bool(data.get("template_content"))}
            )
            return data
        else:
            self.record_result("查询模板详情", False, f"失败: {result.get('detail', result)}")
            return None

    # ==================== 测试场景2: 字段组 upsert 接口测试 ====================

    async def test_upsert_field_group_create(self):
        """测试3: 创建新的字段组和字段"""
        self.log("\n【测试3】创建新字段组")

        data = {
            "page_name": self.page_name,
            "group_name": "测试-场景分类",
            "prompt_template_base": "测试Prompt模板",
            "output_templates": {
                "default": {
                    "template": "测试输出模板",
                    "description": "默认模板"
                }
            },
            "fields": [
                {
                    "field_name": "scene_category",
                    "field_label": "场景分类",
                    "field_type": "select",
                    "fill_instruction": "请选择场景分类",
                    "options": {
                        "source": "static",
                        "items": [
                            {"value": "咨询", "label": "咨询", "fill_instruction": "咨询场景"},
                            {"value": "投诉", "label": "投诉", "fill_instruction": "投诉场景"}
                        ]
                    }
                }
            ]
        }

        result = await self.make_request("POST", "/api/autofill/field_group/upsert", data=data)

        if result.get("code") == 200:
            data = result.get("data", {})
            self.record_result(
                "创建字段组",
                True,
                f"成功创建字段组: {data.get('group_name')}, 包含 {data.get('field_count', 0)} 个字段",
                data
            )
            return data
        else:
            self.record_result("创建字段组", False, f"失败: {result.get('detail', result)}")
            return None

    async def test_upsert_field_group_update(self):
        """测试4: 更新已存在的字段组"""
        self.log("\n【测试4】更新已存在的字段组")

        data = {
            "page_name": self.page_name,
            "group_name": "测试-场景分类",
            "prompt_template_base": "更新后的Prompt模板",
            "fields": [
                {
                    "field_name": "scene_category",
                    "field_label": "场景分类（已更新）",
                    "field_type": "select",
                    "fill_instruction": "请选择场景分类（已更新）"
                },
                {
                    "field_name": "new_field",
                    "field_label": "新增字段",
                    "field_type": "text",
                    "fill_instruction": "请填写新增字段"
                }
            ]
        }

        result = await self.make_request("POST", "/api/autofill/field_group/upsert", data=data)

        if result.get("code") == 200:
            data = result.get("data", {})
            self.record_result(
                "更新字段组",
                True,
                f"成功更新字段组，现在包含 {data.get('field_count', 0)} 个字段",
                data
            )
            return data
        else:
            self.record_result("更新字段组", False, f"失败: {result.get('detail', result)}")
            return None

    async def test_upsert_field_group_page_not_found(self):
        """测试5: 页面不存在时返回404"""
        self.log("\n【测试5】页面不存在时返回404")

        data = {
            "page_name": "不存在的页面",
            "group_name": "测试字段组",
            "fields": [{"field_name": "test", "field_label": "测试"}]
        }

        result = await self.make_request("POST", "/api/autofill/field_group/upsert", data=data)

        if result.get("status_code") == 404 or "not found" in result.get("detail", "").lower():
            self.record_result("页面不存在处理", True, "正确返回404错误")
        else:
            self.record_result("页面不存在处理", False, f"预期返回404，但得到: {result}")

    # ==================== 测试场景3: 查询接口测试 ====================

    async def test_get_field_group(self):
        """测试6: 查询字段组配置"""
        self.log("\n【测试6】查询字段组配置")

        params = {
            "page_name": self.page_name,
            "group_name": "测试-场景分类"
        }

        result = await self.make_request("GET", "/api/autofill/field_group", params=params)

        if result.get("code") == 200:
            data = result.get("data", [])
            if data:
                self.record_result(
                    "查询字段组配置",
                    True,
                    f"成功查询到字段组: {data[0].get('group_name')}",
                    data[0]
                )
            else:
                self.record_result("查询字段组配置", False, "查询结果为空")
        else:
            self.record_result("查询字段组配置", False, f"失败: {result.get('detail', result)}")

    async def test_list_field_spec(self):
        """测试7: 查询字段明细列表"""
        self.log("\n【测试7】查询字段明细列表")

        params = {
            "page_name": self.page_name,
            "group_name": "测试-场景分类"
        }

        result = await self.make_request("GET", "/api/autofill/field_spec/list", params=params)

        if result.get("code") == 200:
            data = result.get("data", [])
            self.record_result(
                "查询字段明细列表",
                True,
                f"成功查询到 {len(data)} 个字段",
                {"field_count": len(data), "fields": [{"name": f["field_name"], "type": f["field_type"]} for f in data]}
            )
        else:
            self.record_result("查询字段明细列表", False, f"失败: {result.get('detail', result)}")

    async def test_list_field_spec_with_name_filter(self):
        """测试8: 使用 field_name 精确查询字段"""
        self.log("\n【测试8】精确查询指定字段")

        params = {
            "page_name": self.page_name,
            "group_name": "测试-场景分类",
            "field_name": "scene_category"
        }

        result = await self.make_request("GET", "/api/autofill/field_spec/list", params=params)

        if result.get("code") == 200:
            data = result.get("data", [])
            if len(data) == 1 and data[0].get("field_name") == "scene_category":
                self.record_result("精确查询字段", True, "成功精确查询到指定字段", data[0])
            else:
                self.record_result("精确查询字段", False, "精确查询结果不匹配", data)
        else:
            self.record_result("精确查询字段", False, f"失败: {result.get('detail', result)}")

    # ==================== 测试场景4: 完整同步流程测试 ====================

    async def test_full_sync_workflow(self):
        """测试9: 完整的模板同步工作流"""
        self.log("\n【测试9】完整模板同步工作流")

        # 步骤1: 获取模板列表
        list_result = await self.make_request("GET", "/api/autofill/summary_template/list")
        if list_result.get("code") != 200:
            self.record_result("完整工作流", False, f"获取模板列表失败: {list_result}")
            return

        templates = list_result.get("data", [])
        if not templates:
            self.record_result("完整工作流", False, "没有可用的模板")
            return

        self.log(f"获取到 {len(templates)} 个模板")

        # 步骤2: 同步场景分类字段
        scene_items = [
            {"value": t["name"], "label": t["name"], "fill_instruction": t.get("summary", "")}
            for t in templates[:5]
        ]

        scene_data = {
            "page_name": self.page_name,
            "group_name": "default",
            "fields": [{
                "field_name": "scene_category",
                "field_label": "场景分类",
                "field_type": "select",
                "fill_instruction": "请选择场景分类",
                "options": {"source": "static", "items": scene_items}
            }]
        }

        scene_result = await self.make_request(
            "POST",
            "/api/autofill/field_group/upsert",
            data=scene_data
        )

        if scene_result.get("code") != 200:
            self.record_result("完整工作流", False, f"创建场景分类字段失败: {scene_result}")
            return

        self.log("场景分类字段同步成功")

        # 步骤3: 为前2个模板创建服务记录字段组
        import re
        success_count = 0

        for template in templates[:2]:
            # 获取模板详情
            detail_result = await self.make_request(
                "GET",
                "/api/autofill/summary_template",
                params={"id": template["id"]}
            )

            if detail_result.get("code") != 200:
                self.log(f"获取模板 {template['name']} 详情失败", "warning")
                continue

            detail = detail_result.get("data", {})
            template_content = detail.get("template_content", "")
            variables = list(set(re.findall(r'\$\{([^}]+)\}', template_content)))

            if not variables:
                self.log(f"模板 {template['name']} 没有变量，跳过")
                continue

            # 创建服务记录字段组
            service_data = {
                "page_name": self.page_name,
                "group_name": f"服务记录-{detail['name']}",
                "output_templates": {
                    "default": {
                        "template": template_content,
                        "description": f"{detail['name']}的输出模板"
                    }
                },
                "fields": [
                    {
                        "field_name": var,
                        "field_label": var,
                        "field_type": "text",
                        "fill_instruction": f"请填写{var}字段"
                    }
                    for var in variables[:5]
                ]
            }

            service_result = await self.make_request(
                "POST",
                "/api/autofill/field_group/upsert",
                data=service_data
            )

            if service_result.get("code") == 200:
                success_count += 1
                self.log(f"服务记录字段组 {detail['name']} 创建成功")
            else:
                self.log(f"服务记录字段组 {detail['name']} 创建失败: {service_result}", "error")

        self.record_result(
            "完整工作流",
            success_count > 0,
            f"成功创建 {success_count} 个服务记录字段组",
            {"templates_processed": min(len(templates), 2), "service_groups_created": success_count}
        )

    # ==================== 运行所有测试 ====================

    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 70)
        print("模板字段同步集成测试")
        print("=" * 70)
        print(f"配置:")
        print(f"  - API URL: {self.base_url}")
        print(f"  - 页面名称: {self.page_name}")
        print("=" * 70)

        # 基础接口测试
        templates = await self.test_summary_template_list()
        if templates:
            await self.test_summary_template_detail(templates[0]["id"])

        # 字段组 upsert 接口测试
        await self.test_upsert_field_group_create()
        await self.test_upsert_field_group_update()
        await self.test_upsert_field_group_page_not_found()

        # 查询接口测试
        await self.test_get_field_group()
        await self.test_list_field_spec()
        await self.test_list_field_spec_with_name_filter()

        # 完整工作流测试
        await self.test_full_sync_workflow()

        # 打印总结
        self.print_summary()

    def print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 70)
        print("测试总结")
        print("=" * 70)

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["success"])
        failed = total - passed

        print(f"总测试数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {failed}")
        print(f"通过率: {passed/total*100:.1f}%" if total > 0 else "N/A")

        if failed > 0:
            print("\n失败的测试:")
            for r in self.test_results:
                if not r["success"]:
                    print(f"  ❌ {r['test_name']}: {r['message']}")

        print("\n通过的测试:")
        for r in self.test_results:
            if r["success"]:
                print(f"  ✅ {r['test_name']}: {r['message']}")

        print("=" * 70)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="模板字段同步集成测试")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"API 基础 URL (默认: {DEFAULT_BASE_URL})")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API Key")
    parser.add_argument("--page-name", default=DEFAULT_PAGE_NAME, help=f"页面名称 (默认: {DEFAULT_PAGE_NAME})")

    args = parser.parse_args()

    test = TemplateSyncIntegrationTest(
        base_url=args.base_url,
        api_key=args.api_key,
        page_name=args.page_name
    )

    asyncio.run(test.run_all_tests())


if __name__ == "__main__":
    main()
