"""
测试 Public API 字段组相关接口
测试以下接口:
1. POST /api/autofill/field_group/upsert - 创建或更新字段组（含批量字段）
2. GET/POST /api/autofill/field_group - 查询字段组配置
3. GET/POST /api/autofill/field_spec/list - 查询字段明细列表
4. GET/POST /api/autofill/summary_template/list - 查询模板列表
5. GET/POST /api/autofill/summary_template - 查询模板详情
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from typing import Dict, Any, List
import json


# 测试配置
BASE_URL = "http://localhost:9999"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"  # 使用正确的 API Key


class PublicAPITest:
    """Public API 测试类"""

    def __init__(self, base_url: str = BASE_URL, api_key: str = API_KEY):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.test_results = []

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

    def log_result(self, test_name: str, success: bool, message: str = "", data: Any = None):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "message": message,
            "data": data
        }
        self.test_results.append(result)
        status = "✅ 通过" if success else "❌ 失败"
        print(f"\n{status} - {test_name}")
        if message:
            print(f"   消息: {message}")
        if data:
            print(f"   数据: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}...")

    # ==================== 测试接口 1: 字段组批量创建/更新 ====================

    async def test_upsert_field_group_create_new(self):
        """测试1: 创建新的字段组和字段"""
        test_name = "创建新字段组和字段"
        endpoint = "/api/autofill/field_group/upsert"

        data = {
            "page_name": "用户信息页",
            "group_name": "测试字段组-场景分类",
            "prompt_template_base": "这是一个测试模板",
            "output_templates": {
                "default": {
                    "template": "测试模板内容",
                    "description": "默认输出模板"
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
                            {"value": "咨询", "label": "咨询", "fill_instruction": "用户咨询类场景"},
                            {"value": "投诉", "label": "投诉", "fill_instruction": "用户投诉类场景"},
                            {"value": "建议", "label": "建议", "fill_instruction": "用户建议类场景"}
                        ]
                    }
                }
            ]
        }

        result = await self.make_request("POST", endpoint, data=data)

        if result.get("code") == 200:
            self.log_result(test_name, True, "成功创建字段组和字段", result.get("data"))
        else:
            self.log_result(test_name, False, f"创建失败: {result.get('detail', result)}")

    async def test_upsert_field_group_update_existing(self):
        """测试2: 更新已存在的字段组"""
        test_name = "更新已存在的字段组"
        endpoint = "/api/autofill/field_group/upsert"

        data = {
            "page_name": "用户信息页",
            "group_name": "测试字段组-场景分类",
            "prompt_template_base": "这是更新后的测试模板",
            "output_templates": {
                "default": {
                    "template": "更新后的模板内容",
                    "description": "更新后的默认输出模板"
                }
            },
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

        result = await self.make_request("POST", endpoint, data=data)

        if result.get("code") == 200:
            self.log_result(test_name, True, "成功更新字段组和字段", result.get("data"))
        else:
            self.log_result(test_name, False, f"更新失败: {result.get('detail', result)}")

    async def test_upsert_field_group_page_not_found(self):
        """测试3: 页面不存在时返回404"""
        test_name = "页面不存在时返回404"
        endpoint = "/api/autofill/field_group/upsert"

        data = {
            "page_name": "不存在的页面",
            "group_name": "测试字段组",
            "fields": [
                {
                    "field_name": "test_field",
                    "field_label": "测试字段",
                    "field_type": "text"
                }
            ]
        }

        result = await self.make_request("POST", endpoint, data=data)

        if result.get("status_code") == 404 or "not found" in result.get("detail", "").lower():
            self.log_result(test_name, True, "正确返回404错误")
        else:
            self.log_result(test_name, False, f"预期返回404，但得到: {result}")

    async def test_upsert_field_group_with_service_record(self):
        """测试4: 创建服务记录字段组（模拟模板同步场景）"""
        test_name = "创建服务记录字段组"
        endpoint = "/api/autofill/field_group/upsert"

        data = {
            "page_name": "用户信息页",
            "group_name": "服务记录-客户信息模板",
            "prompt_template_base": "请根据对话提取客户信息",
            "output_templates": {
                "default": {
                    "template": "客户姓名: ${customer_name}, 电话: ${phone}, 地址: ${address}",
                    "description": "客户信息输出模板"
                }
            },
            "fields": [
                {
                    "field_name": "customer_name",
                    "field_label": "客户姓名",
                    "field_type": "text",
                    "fill_instruction": "请填写客户姓名"
                },
                {
                    "field_name": "phone",
                    "field_label": "联系电话",
                    "field_type": "text",
                    "fill_instruction": "请填写联系电话"
                },
                {
                    "field_name": "address",
                    "field_label": "地址",
                    "field_type": "text",
                    "fill_instruction": "请填写地址"
                }
            ]
        }

        result = await self.make_request("POST", endpoint, data=data)

        if result.get("code") == 200:
            self.log_result(test_name, True, "成功创建服务记录字段组", result.get("data"))
        else:
            self.log_result(test_name, False, f"创建失败: {result.get('detail', result)}")

    # ==================== 测试接口 2: 查询字段组配置 ====================

    async def test_get_field_group_by_page_and_group_name(self):
        """测试5: 通过 page_name + group_name 查询字段组"""
        test_name = "通过page_name和group_name查询字段组"
        endpoint = "/api/autofill/field_group"

        # 测试 GET 方法
        params = {
            "page_name": "用户信息页",
            "group_name": "测试字段组-场景分类"
        }

        result = await self.make_request("GET", endpoint, params=params)

        if result.get("code") == 200:
            data = result.get("data", [])
            if len(data) > 0 and data[0].get("group_name") == "测试字段组-场景分类":
                self.log_result(test_name, True, "GET方法查询成功", data)
            else:
                self.log_result(test_name, False, "查询结果为空或字段组名称不匹配", data)
        else:
            self.log_result(test_name, False, f"查询失败: {result.get('detail', result)}")

    async def test_get_field_group_post_method(self):
        """测试6: 使用 POST 方法查询字段组"""
        test_name = "使用POST方法查询字段组"
        endpoint = "/api/autofill/field_group"

        data = {
            "page_name": "用户信息页",
            "group_name": "服务记录-客户信息模板"
        }

        result = await self.make_request("POST", endpoint, data=data)

        if result.get("code") == 200:
            data = result.get("data", [])
            if len(data) > 0:
                self.log_result(test_name, True, "POST方法查询成功", data)
            else:
                self.log_result(test_name, False, "查询结果为空", data)
        else:
            self.log_result(test_name, False, f"查询失败: {result.get('detail', result)}")

    async def test_get_field_group_not_found(self):
        """测试7: 查询不存在的字段组返回空列表"""
        test_name = "查询不存在的字段组"
        endpoint = "/api/autofill/field_group"

        params = {
            "page_name": "用户信息页",
            "group_name": "不存在的字段组"
        }

        result = await self.make_request("GET", endpoint, params=params)

        if result.get("code") == 200:
            data = result.get("data", [])
            if len(data) == 0:
                self.log_result(test_name, True, "正确返回空列表")
            else:
                self.log_result(test_name, False, "预期返回空列表，但得到数据", data)
        else:
            self.log_result(test_name, False, f"查询失败: {result.get('detail', result)}")

    async def test_get_field_group_page_not_found(self):
        """测试8: 查询不存在的页面返回空列表"""
        test_name = "查询不存在的页面"
        endpoint = "/api/autofill/field_group"

        params = {
            "page_name": "不存在的页面",
            "group_name": "测试字段组"
        }

        result = await self.make_request("GET", endpoint, params=params)

        if result.get("code") == 200:
            data = result.get("data", [])
            if len(data) == 0:
                self.log_result(test_name, True, "正确返回空列表")
            else:
                self.log_result(test_name, False, "预期返回空列表，但得到数据", data)
        else:
            self.log_result(test_name, False, f"查询失败: {result.get('detail', result)}")

    # ==================== 测试接口 3: 查询字段明细列表 ====================

    async def test_list_field_spec_by_page_and_group(self):
        """测试9: 通过 page_name + group_name 查询字段明细"""
        test_name = "通过page_name和group_name查询字段明细"
        endpoint = "/api/autofill/field_spec/list"

        params = {
            "page_name": "用户信息页",
            "group_name": "测试字段组-场景分类"
        }

        result = await self.make_request("GET", endpoint, params=params)

        if result.get("code") == 200:
            data = result.get("data", [])
            if len(data) > 0:
                self.log_result(test_name, True, f"查询到 {len(data)} 个字段", data)
            else:
                self.log_result(test_name, False, "查询结果为空", data)
        else:
            self.log_result(test_name, False, f"查询失败: {result.get('detail', result)}")

    async def test_list_field_spec_with_field_name(self):
        """测试10: 通过 page_name + group_name + field_name 精确查询字段"""
        test_name = "精确查询指定字段"
        endpoint = "/api/autofill/field_spec/list"

        params = {
            "page_name": "用户信息页",
            "group_name": "服务记录-客户信息模板",
            "field_name": "customer_name"
        }

        result = await self.make_request("GET", endpoint, params=params)

        if result.get("code") == 200:
            data = result.get("data", [])
            if len(data) == 1 and data[0].get("field_name") == "customer_name":
                self.log_result(test_name, True, "精确查询成功", data)
            else:
                self.log_result(test_name, False, "精确查询结果不匹配", data)
        else:
            self.log_result(test_name, False, f"查询失败: {result.get('detail', result)}")

    async def test_list_field_spec_post_method(self):
        """测试11: 使用 POST 方法查询字段明细"""
        test_name = "使用POST方法查询字段明细"
        endpoint = "/api/autofill/field_spec/list"

        data = {
            "page_name": "用户信息页",
            "group_name": "测试字段组-场景分类"
        }

        result = await self.make_request("POST", endpoint, data=data)

        if result.get("code") == 200:
            data = result.get("data", [])
            self.log_result(test_name, True, f"查询到 {len(data)} 个字段", data)
        else:
            self.log_result(test_name, False, f"查询失败: {result.get('detail', result)}")

    async def test_list_field_spec_group_not_found(self):
        """测试12: 查询不存在的字段组返回空列表"""
        test_name = "查询不存在的字段组的字段"
        endpoint = "/api/autofill/field_spec/list"

        params = {
            "page_name": "用户信息页",
            "group_name": "不存在的字段组"
        }

        result = await self.make_request("GET", endpoint, params=params)

        if result.get("code") == 200:
            data = result.get("data", [])
            if len(data) == 0:
                self.log_result(test_name, True, "正确返回空列表")
            else:
                self.log_result(test_name, False, "预期返回空列表", data)
        else:
            self.log_result(test_name, False, f"查询失败: {result.get('detail', result)}")

    # ==================== 测试接口 4 & 5: 模板相关接口 ====================

    async def test_list_summary_templates(self):
        """测试13: 查询模板列表"""
        test_name = "查询模板列表"
        endpoint = "/api/autofill/summary_template/list"

        result = await self.make_request("GET", endpoint)

        if result.get("code") == 200:
            data = result.get("data", [])
            self.log_result(test_name, True, f"查询到 {len(data)} 个模板", data)
        else:
            self.log_result(test_name, False, f"查询失败: {result.get('detail', result)}")

    async def test_list_summary_templates_with_class_name(self):
        """测试14: 使用 class_name 过滤模板列表"""
        test_name = "使用class_name过滤模板列表"
        endpoint = "/api/autofill/summary_template/list"

        params = {"class_name": "测试分类"}
        result = await self.make_request("GET", endpoint, params=params)

        if result.get("code") == 200:
            data = result.get("data", [])
            self.log_result(test_name, True, f"过滤后查询到 {len(data)} 个模板", data)
        else:
            self.log_result(test_name, False, f"查询失败: {result.get('detail', result)}")

    async def test_get_summary_template_detail(self):
        """测试15: 查询模板详情"""
        test_name = "查询模板详情"
        endpoint = "/api/autofill/summary_template"

        # 先获取模板列表
        list_result = await self.make_request("GET", "/api/autofill/summary_template/list")
        templates = list_result.get("data", [])

        if not templates:
            self.log_result(test_name, False, "没有可用的模板进行测试")
            return

        template_id = templates[0].get("id")
        params = {"id": template_id}

        result = await self.make_request("GET", endpoint, params=params)

        if result.get("code") == 200:
            data = result.get("data")
            if data and data.get("id") == template_id:
                self.log_result(test_name, True, "成功获取模板详情", data)
            else:
                self.log_result(test_name, False, "模板详情不匹配", data)
        else:
            self.log_result(test_name, False, f"查询失败: {result.get('detail', result)}")

    # ==================== 综合测试场景 ====================

    async def test_full_template_sync_workflow(self):
        """测试16: 完整的模板同步工作流"""
        test_name = "完整模板同步工作流"

        # 步骤1: 获取模板列表
        list_result = await self.make_request(
            "GET",
            "/api/autofill/summary_template/list"
        )

        if list_result.get("code") != 200:
            self.log_result(test_name, False, f"获取模板列表失败: {list_result}")
            return

        templates = list_result.get("data", [])
        if not templates:
            self.log_result(test_name, False, "没有可用的模板进行测试")
            return

        # 步骤2: 获取第一个模板的详情
        template = templates[0]
        detail_result = await self.make_request(
            "GET",
            "/api/autofill/summary_template",
            params={"id": template["id"]}
        )

        if detail_result.get("code") != 200:
            self.log_result(test_name, False, f"获取模板详情失败: {detail_result}")
            return

        template_detail = detail_result.get("data", {})
        template_content = template_detail.get("template_content", "")

        # 步骤3: 解析模板变量
        import re
        variables = list(set(re.findall(r'\$\{([^}]+)\}', template_content)))

        # 步骤4: 创建/更新"场景分类"字段（在default字段组）
        scene_field_data = {
            "page_name": "用户信息页",
            "group_name": "default",
            "fields": [
                {
                    "field_name": "scene_category",
                    "field_label": "场景分类",
                    "field_type": "select",
                    "fill_instruction": "请选择场景分类",
                    "options": {
                        "source": "static",
                        "items": [
                            {
                                "value": t["name"],
                                "label": t["name"],
                                "fill_instruction": t.get("summary", "")
                            }
                            for t in templates[:5]  # 取前5个模板作为选项
                        ]
                    }
                }
            ]
        }

        upsert_result = await self.make_request(
            "POST",
            "/api/autofill/field_group/upsert",
            data=scene_field_data
        )

        if upsert_result.get("code") != 200:
            self.log_result(test_name, False, f"创建场景分类字段失败: {upsert_result}")
            return

        # 步骤5: 为每个模板创建服务记录字段组
        for t in templates[:2]:  # 只测试前2个模板
            template_name = t["name"]
            template_content = t.get("template_content", "")
            variables = list(set(re.findall(r'\$\{([^}]+)\}', template_content)))

            if not variables:
                continue

            service_record_data = {
                "page_name": "用户信息页",
                "group_name": f"服务记录-{template_name}",
                "output_templates": {
                    "default": {
                        "template": template_content,
                        "description": f"{template_name}的输出模板"
                    }
                },
                "fields": [
                    {
                        "field_name": var,
                        "field_label": var,
                        "field_type": "text",
                        "fill_instruction": f"请填写{var}字段"
                    }
                    for var in variables[:5]  # 最多5个字段
                ]
            }

            result = await self.make_request(
                "POST",
                "/api/autofill/field_group/upsert",
                data=service_record_data
            )

            if result.get("code") != 200:
                self.log_result(test_name, False, f"创建服务记录字段组失败: {result}")
                return

        self.log_result(test_name, True, f"成功完成模板同步工作流，处理了 {len(templates[:2])} 个模板")

    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("开始 Public API 字段组接口测试")
        print("=" * 60)

        # 字段组批量创建/更新测试
        print("\n【字段组批量创建/更新接口测试】")
        await self.test_upsert_field_group_create_new()
        await self.test_upsert_field_group_update_existing()
        await self.test_upsert_field_group_page_not_found()
        await self.test_upsert_field_group_with_service_record()

        # 查询字段组配置测试
        print("\n【查询字段组配置接口测试】")
        await self.test_get_field_group_by_page_and_group_name()
        await self.test_get_field_group_post_method()
        await self.test_get_field_group_not_found()
        await self.test_get_field_group_page_not_found()

        # 查询字段明细列表测试
        print("\n【查询字段明细列表接口测试】")
        await self.test_list_field_spec_by_page_and_group()
        await self.test_list_field_spec_with_field_name()
        await self.test_list_field_spec_post_method()
        await self.test_list_field_spec_group_not_found()

        # 模板相关接口测试
        print("\n【模板相关接口测试】")
        await self.test_list_summary_templates()
        await self.test_list_summary_templates_with_class_name()
        await self.test_get_summary_template_detail()

        # 综合测试场景
        print("\n【综合测试场景】")
        await self.test_full_template_sync_workflow()

        # 打印测试总结
        self.print_summary()

    def print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)

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
                    print(f"  - {r['test_name']}: {r['message']}")


async def main():
    """主函数"""
    # 从环境变量或命令行参数获取配置
    import argparse

    parser = argparse.ArgumentParser(description="Public API 字段组接口测试")
    parser.add_argument("--url", default=BASE_URL, help=f"API 基础 URL (默认: {BASE_URL})")
    parser.add_argument("--api-key", default=API_KEY, help="API Key")
    parser.add_argument("--test", help="运行指定测试")

    args = parser.parse_args()

    tester = PublicAPITest(base_url=args.url, api_key=args.api_key)

    if args.test:
        # 运行指定测试
        test_method = getattr(tester, args.test, None)
        if test_method:
            await test_method()
        else:
            print(f"未找到测试: {args.test}")
            print(f"可用测试: {[m for m in dir(tester) if m.startswith('test_')]}")
    else:
        # 运行所有测试
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
