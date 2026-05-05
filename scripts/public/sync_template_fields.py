#!/usr/bin/env python3
"""
模板字段同步脚本

根据总结模板自动创建/更新字段组和字段，实现模板与字段配置的同步。

核心流程:
1. 查询总结模板列表，获取模板名称、摘要和模板内容
2. 创建/更新"场景分类"下拉字段（在default字段组）
3. 解析模板内容中的变量（如 ${customer_name}），为每个模板创建对应的字段组和服务记录字段

使用方法:
    python scripts/sync_template_fields.py --api-key <your_api_key> [--page-name <page_name>] [--base-url <base_url>]

示例:
    python scripts/sync_template_fields.py --api-key af_your_api_key_here
    python scripts/sync_template_fields.py --api-key af_your_api_key_here --page-name "用户信息页" --dry-run
"""

import asyncio
import argparse
import json
import re
import sys
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import httpx


# 默认配置
DEFAULT_BASE_URL = "http://localhost:9999"
DEFAULT_PAGE_NAME = "用户信息页"
DEFAULT_SCENE_FIELD_NAME = "scene_category"
DEFAULT_SCENE_FIELD_LABEL = "场景分类"


@dataclass
class Template:
    """模板数据类"""
    id: int
    name: str
    summary: str
    class_name: str
    template_content: str = ""
    variables: List[str] = None

    def __post_init__(self):
        if self.variables is None:
            self.variables = []


@dataclass
class SyncResult:
    """同步结果数据类"""
    success: bool
    message: str
    data: Any = None


class TemplateFieldSync:
    """模板字段同步器"""

    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL, page_name: str = DEFAULT_PAGE_NAME):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.page_name = page_name
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.sync_results: List[SyncResult] = []

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

    def extract_variables(self, template_content: str) -> List[str]:
        """
        提取模板中的变量名
        如 ${customer_name} -> customer_name
        """
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, template_content)
        return list(set(matches))  # 去重

    async def get_template_list(self, class_name: str = None) -> List[Template]:
        """
        获取模板列表
        """
        endpoint = "/api/autofill/summary_template/list"
        params = {}
        if class_name:
            params["class_name"] = class_name

        result = await self.make_request("GET", endpoint, params=params)

        if result.get("code") != 200:
            print(f"❌ 获取模板列表失败: {result.get('detail', result)}")
            return []

        templates_data = result.get("data", [])
        templates = []

        for t in templates_data:
            template = Template(
                id=t["id"],
                name=t["name"],
                summary=t.get("summary", ""),
                class_name=t.get("class_name", "")
            )
            templates.append(template)

        return templates

    async def get_template_detail(self, template_id: int) -> Optional[Template]:
        """
        获取模板详情
        """
        endpoint = "/api/autofill/summary_template"
        params = {"id": template_id}

        result = await self.make_request("GET", endpoint, params=params)

        if result.get("code") != 200:
            print(f"❌ 获取模板详情失败 (ID: {template_id}): {result.get('detail', result)}")
            return None

        data = result.get("data", {})
        template_content = data.get("template_content", "")
        variables = self.extract_variables(template_content)

        return Template(
            id=data["id"],
            name=data["name"],
            summary=data.get("summary", ""),
            class_name=data.get("class_name", ""),
            template_content=template_content,
            variables=variables
        )

    async def upsert_field_group(self, group_name: str, fields: List[Dict],
                                  output_templates: Dict = None,
                                  prompt_template_base: str = None,
                                  dry_run: bool = False) -> SyncResult:
        """
        创建或更新字段组
        """
        if dry_run:
            return SyncResult(
                success=True,
                message=f"[Dry Run] 将创建/更新字段组: {group_name}, 包含 {len(fields)} 个字段",
                data={"group_name": group_name, "fields": fields}
            )

        endpoint = "/api/autofill/field_group/upsert"
        data = {
            "page_name": self.page_name,
            "group_name": group_name,
            "fields": fields
        }

        if output_templates:
            data["output_templates"] = output_templates
        if prompt_template_base:
            data["prompt_template_base"] = prompt_template_base

        result = await self.make_request("POST", endpoint, data=data)

        if result.get("code") == 200:
            return SyncResult(
                success=True,
                message=f"✅ 成功同步字段组: {group_name}",
                data=result.get("data")
            )
        else:
            return SyncResult(
                success=False,
                message=f"❌ 同步字段组失败: {group_name} - {result.get('detail', result)}",
                data=result
            )

    async def sync_scene_category_field(self, templates: List[Template], dry_run: bool = False) -> SyncResult:
        """
        同步"场景分类"字段
        在default字段组中创建一个select类型的字段，选项为所有模板名称
        """
        print(f"\n📋 步骤1: 同步场景分类字段到 default 字段组")

        # 构建选项列表
        items = []
        for t in templates:
            summary = t.summary if t.summary else f"{t.name}场景"
            items.append({
                "value": t.name,
                "label": t.name,
                "fill_instruction": summary
            })

        fields = [{
            "field_name": DEFAULT_SCENE_FIELD_NAME,
            "field_label": DEFAULT_SCENE_FIELD_LABEL,
            "field_type": "select",
            "fill_instruction": "请选择场景分类",
            "options": {
                "source": "static",
                "items": items
            }
        }]

        result = await self.upsert_field_group(
            group_name="default",
            fields=fields,
            dry_run=dry_run
        )

        self.sync_results.append(result)
        print(f"   {result.message}")

        return result

    async def sync_service_record_fields(self, templates: List[Template],
                                          max_templates: int = None,
                                          dry_run: bool = False) -> List[SyncResult]:
        """
        同步服务记录字段组
        为每个模板创建一个字段组，字段为模板中的变量
        """
        print(f"\n📋 步骤2: 同步服务记录字段组")

        results = []
        templates_to_process = templates[:max_templates] if max_templates else templates

        for i, template in enumerate(templates_to_process, 1):
            print(f"\n   [{i}/{len(templates_to_process)}] 处理模板: {template.name}")

            # 获取模板详情（包含变量）
            detail = await self.get_template_detail(template.id)
            if not detail:
                result = SyncResult(
                    success=False,
                    message=f"❌ 无法获取模板详情: {template.name}"
                )
                results.append(result)
                self.sync_results.append(result)
                continue

            if not detail.variables:
                print(f"      ℹ️ 模板中没有变量，跳过")
                continue

            print(f"      发现 {len(detail.variables)} 个变量: {', '.join(detail.variables[:5])}")
            if len(detail.variables) > 5:
                print(f"      ... 还有 {len(detail.variables) - 5} 个变量")

            # 构建字段列表
            fields = []
            for var in detail.variables:
                # 根据字段名生成更有意义的 fill_instruction
                field_instructions_map = {
                    "customer_name": "车主姓名，如：张先生、李女士",
                    "contact_phone": "联系电话，如：13800138000",
                    "vehicle_system": "车系信息，如：比亚迪汉、特斯拉Model 3",
                    "vin_code": "车辆识别代号(VIN码)，17位字母数字组合"
                }
                fill_instruction = field_instructions_map.get(var, f"请填写{var}")
                fields.append({
                    "field_name": var,
                    "field_label": var,
                    "field_type": "text",
                    "fill_instruction": fill_instruction
                })

            # 构建输出模板
            output_templates = {
                "default": {
                    "template": detail.template_content,
                    "description": f"{detail.name}的输出模板"
                }
            }

            # 创建字段组 - 使用正确的模板格式，包含 {{fields_instructions}} 占位符
            group_name = f"服务记录-{detail.name}"
            prompt_template = f"""你是一个智能填单助手。请根据以下对话内容，提取【{detail.name}】相关的字段信息。

需要提取的字段：
{{{{fields_instructions}}}}

对话内容：
{{{{query}}}}

请严格按照字段要求提取信息，并以JSON格式返回结果。"""
            result = await self.upsert_field_group(
                group_name=group_name,
                fields=fields,
                output_templates=output_templates,
                prompt_template_base=prompt_template,
                dry_run=dry_run
            )

            results.append(result)
            self.sync_results.append(result)
            print(f"      {result.message}")

        return results

    async def verify_sync_results(self) -> bool:
        """
        验证同步结果
        """
        print(f"\n📋 步骤3: 验证同步结果")

        all_success = True

        # 验证场景分类字段
        print(f"\n   验证场景分类字段...")
        endpoint = "/api/autofill/field_spec/list"
        params = {
            "page_name": self.page_name,
            "group_name": "default",
            "field_name": DEFAULT_SCENE_FIELD_NAME
        }

        result = await self.make_request("GET", endpoint, params=params)
        if result.get("code") == 200:
            data = result.get("data", [])
            if data:
                print(f"   ✅ 场景分类字段已创建: {data[0]['field_label']}")
            else:
                print(f"   ❌ 场景分类字段未找到")
                all_success = False
        else:
            print(f"   ❌ 验证失败: {result.get('detail', result)}")
            all_success = False

        # 验证服务记录字段组
        print(f"\n   验证服务记录字段组...")
        success_count = sum(1 for r in self.sync_results if r.success)
        print(f"   ✅ 成功同步: {success_count}/{len(self.sync_results)} 个字段组")

        return all_success

    async def run(self, class_name: str = None, max_templates: int = None, dry_run: bool = False):
        """
        运行同步流程
        """
        print("=" * 60)
        print("模板字段同步脚本")
        print("=" * 60)
        print(f"配置信息:")
        print(f"  - API URL: {self.base_url}")
        print(f"  - 页面名称: {self.page_name}")
        print(f"  - 模板分类: {class_name or '全部'}")
        print(f"  - 最大模板数: {max_templates or '无限制'}")
        print(f"  - 试运行模式: {dry_run}")
        print("=" * 60)

        # 步骤1: 获取模板列表
        print(f"\n📋 获取模板列表...")
        templates = await self.get_template_list(class_name=class_name)
        if not templates:
            print("❌ 没有找到模板，同步结束")
            return

        print(f"✅ 找到 {len(templates)} 个模板")
        for t in templates[:5]:
            print(f"   - {t.name} ({t.class_name})")
        if len(templates) > 5:
            print(f"   ... 还有 {len(templates) - 5} 个模板")

        # 步骤2: 同步场景分类字段
        await self.sync_scene_category_field(templates, dry_run=dry_run)

        # 步骤3: 同步服务记录字段组
        await self.sync_service_record_fields(
            templates,
            max_templates=max_templates,
            dry_run=dry_run
        )

        # 步骤4: 验证结果（非试运行模式）
        if not dry_run:
            await self.verify_sync_results()

        # 打印总结
        self.print_summary()

    def print_summary(self):
        """打印同步总结"""
        print("\n" + "=" * 60)
        print("同步总结")
        print("=" * 60)

        total = len(self.sync_results)
        success = sum(1 for r in self.sync_results if r.success)
        failed = total - success

        print(f"总同步任务: {total}")
        print(f"成功: {success}")
        print(f"失败: {failed}")
        print(f"成功率: {success/total*100:.1f}%" if total > 0 else "N/A")

        if failed > 0:
            print("\n失败的任务:")
            for r in self.sync_results:
                    print(f"  - {r.message}")

        print("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="模板字段同步脚本 - 根据总结模板自动创建/更新字段组和字段"
    )
    parser.add_argument(
        "--api-key",
        required=True,
        help="API Key (格式: af_xxx)"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API 基础 URL (默认: {DEFAULT_BASE_URL})"
    )
    parser.add_argument(
        "--page-name",
        default=DEFAULT_PAGE_NAME,
        help=f"页面名称 (默认: {DEFAULT_PAGE_NAME})"
    )
    parser.add_argument(
        "--class-name",
        help="按分类名称过滤模板"
    )
    parser.add_argument(
        "--max-templates",
        type=int,
        help="最大处理的模板数量（用于测试）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行模式，不实际创建/修改数据"
    )

    args = parser.parse_args()

    # 创建同步器并运行
    sync = TemplateFieldSync(
        api_key=args.api_key,
        base_url=args.base_url,
        page_name=args.page_name
    )

    asyncio.run(sync.run(
        class_name=args.class_name,
        max_templates=args.max_templates,
        dry_run=args.dry_run
    ))


if __name__ == "__main__":
    main()
