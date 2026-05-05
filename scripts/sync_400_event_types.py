#!/usr/bin/env python3
"""
400电话事件类型数据同步脚本

功能:
1. 查询分类为"400电话"的一级下拉选项
2. 创建一级事件类型字段
3. 为每个一级选项查询二三级子选项
4. 展平二三级选项并创建对应字段

使用方法:
    python scripts/sync_400_event_types.py --api-key "af_xxx" [--dry-run]

参数:
    --api-key: API Key (必需)
    --base-url: API基础地址 (默认: http://localhost:9999)
    --class-name: 分类名称 (默认: 400电话)
    --page-name: 页面名称 (默认: 用户信息页)
    --group-name: 字段组名称 (默认: default)
    --dry-run: 只打印日志，不实际创建
"""

import argparse
import asyncio
import sys
from typing import Any, Dict, List, Optional

import httpx


class EventTypeSyncer:
    """400电话事件类型同步器"""

    def __init__(self, api_key: str, base_url: str = "http://localhost:9999"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """发送HTTP请求"""
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                json=json_data,
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_dropdown_options(
        self,
        class_name: str,
        parent_id: int = 0,
        tree: bool = False,
    ) -> List[Dict]:
        """
        查询下拉选项列表

        Args:
            class_name: 分类名称 (如"400电话")
            parent_id: 父选项ID (0表示顶级)
            tree: 是否返回树形结构 (默认False)

        Returns:
            tree=False: [{id, option_value, summary, has_children}, ...]
            tree=True:  [{id, option_value, summary, children: [...]}, ...]
        """
        params = {
            "class_name": class_name,
            "parent_id": parent_id,
            "tree": tree,
        }

        result = await self._request(
            "GET",
            "/api/autofill/dropdown_options/list",
            params=params,
        )

        if result.get("code") != 200:
            raise Exception(f"查询下拉选项失败: {result.get('msg')}")

        return result.get("data", [])

    async def upsert_field_group(
        self,
        page_name: str,
        group_name: str,
        fields: List[Dict],
    ) -> Dict:
        """
        创建或更新字段组

        Args:
            page_name: 页面名称
            group_name: 字段组名称
            fields: 字段列表

        Returns:
            操作结果
        """
        json_data = {
            "page_name": page_name,
            "group_name": group_name,
            "fields": fields,
        }

        result = await self._request(
            "POST",
            "/api/autofill/field_group/upsert",
            json_data=json_data,
        )

        if result.get("code") != 200:
            raise Exception(f"创建字段组失败: {result.get('msg')}")

        return result.get("data", {})

    async def get_all_descendants(
        self, class_name: str, parent_id: int
    ) -> List[Dict]:
        """
        递归获取所有后代选项

        Args:
            class_name: 分类名称
            parent_id: 父选项ID

        Returns:
            所有后代选项的展平列表
        """
        result = []

        # 获取直接子选项
        children = await self.get_dropdown_options(class_name, parent_id)

        for child in children:
            child_id = child.get("id")
            child_value = child.get("option_value", "")

            # 获取孙选项
            grandchildren = await self.get_dropdown_options(class_name, child_id)

            if grandchildren:
                # 有三级选项，展平
                for grandchild in grandchildren:
                    grandchild_id = grandchild.get("id")
                    grandchild_value = grandchild.get("option_value", "")

                    result.append({
                        "value": f"{child_id}-{grandchild_id}",
                        "label": f"{child_value} - {grandchild_value}",
                        "fill_instruction": f"请填写{child_value} - {grandchild_value}",
                    })
            else:
                # 只有二级选项
                result.append({
                    "value": str(child_id),
                    "label": child_value,
                    "fill_instruction": f"请填写{child_value}",
                })

        return result

    async def sync_first_level(
        self,
        page_name: str,
        group_name: str,
        class_name: str = "400电话",
        dry_run: bool = False,
    ):
        """
        同步一级事件类型

        Args:
            page_name: 页面名称
            group_name: 字段组名称
            class_name: 分类名称
            dry_run: 是否只打印日志
        """
        print("\n[步骤1] 查询一级事件类型...")
        print(f"  分类: {class_name}, parent_id: 0")

        first_level_options = await self.get_dropdown_options(class_name, parent_id=0)

        if not first_level_options:
            print("  ⚠️ 没有一级事件类型数据")
            return []

        print(f"  ✅ 获取到 {len(first_level_options)} 个一级事件类型")
        for opt in first_level_options:
            print(f"     - {opt.get('option_value')} (ID: {opt.get('id')})")

        # 构建字段配置
        field_options = [
            {
                "value": str(opt.get("id")),
                "label": opt.get("option_value", ""),
                "fill_instruction": f"请填写{opt.get('option_value', '')}",
            }
            for opt in first_level_options
        ]

        fields = [
            {
                "field_name": "一级事件类型",
                "field_label": "一级事件类型",
                "field_type": "select",
                "fill_instruction": "请选择一级事件类型",
                "options": {
                    "source": "static",
                    "items": field_options,
                },
            }
        ]

        print("\n[步骤2] 创建一级事件类型字段...")
        print(f"  页面: {page_name}")
        print(f"  字段组: {group_name}")
        print("  字段名: 一级事件类型")
        print(f"  选项数量: {len(field_options)}")

        if dry_run:
            print("  [Dry Run] 跳过实际创建")
            return first_level_options

        try:
            await self.upsert_field_group(
                page_name=page_name,
                group_name=group_name,
                fields=fields,
            )
            print("  ✅ 创建成功")
            return first_level_options
        except Exception as e:
            if "already exists" in str(e).lower():
                print("  ⚠️ 字段已存在，跳过")
                return first_level_options
            raise

    async def sync_second_third_level(
        self,
        page_name: str,
        group_name: str,
        first_level_options: List[Dict],
        class_name: str = "400电话",
        dry_run: bool = False,
    ):
        """
        同步二三级事件类型

        Args:
            page_name: 页面名称
            group_name: 字段组名称
            first_level_options: 一级事件类型列表
            class_name: 分类名称
            dry_run: 是否只打印日志
        """
        print("\n[步骤3] 同步二三级事件类型...")
        print(f"  共 {len(first_level_options)} 个一级事件类型需要处理\n")

        for first_level in first_level_options:
            first_id = first_level.get("id")
            first_value = first_level.get("option_value", "")

            print(f"  处理: {first_value} (ID: {first_id})")

            # 获取二三级选项
            try:
                flat_options = await self.get_all_descendants(class_name, first_id)
            except Exception as e:
                print(f"    ❌ 获取子选项失败: {e}")
                continue

            if not flat_options:
                print("    ⚠️ 没有二三级选项，跳过")
                continue

            print(f"    ✅ 获取到 {len(flat_options)} 个选项")

            # 构建字段名（使用原始值，保持中文）
            field_name = f"{first_value}-二三级"
            field_label = f"{first_value}-二三级"

            fields = [
                {
                    "field_name": field_name,
                    "field_label": field_label,
                    "field_type": "select",
                    "fill_instruction": "请选择二三级事件类型",
                    "options": {
                        "source": "static",
                        "items": flat_options,
                    },
                }
            ]

            print(f"    字段名: {field_name}")
            print("    选项示例:")
            for opt in flat_options[:3]:
                print(f"      - {opt['label']}")
            if len(flat_options) > 3:
                print(f"      ... 还有 {len(flat_options) - 3} 个选项")

            if dry_run:
                print("    [Dry Run] 跳过实际创建\n")
                continue

            try:
                await self.upsert_field_group(
                    page_name=page_name,
                    group_name=group_name,
                    fields=fields,
                )
                print("    ✅ 创建成功\n")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("    ⚠️ 字段已存在，跳过\n")
                else:
                    print(f"    ❌ 创建失败: {e}\n")

    async def sync(
        self,
        page_name: str = "用户信息页",
        group_name: str = "default",
        class_name: str = "400电话",
        dry_run: bool = False,
    ):
        """
        执行完整同步

        Args:
            page_name: 页面名称
            group_name: 字段组名称
            class_name: 分类名称
            dry_run: 是否只打印日志
        """
        print("=" * 60)
        print("400电话事件类型数据同步")
        print("=" * 60)
        print(f"API地址: {self.base_url}")
        print(f"分类: {class_name}")
        print(f"页面: {page_name}")
        print(f"字段组: {group_name}")
        print(f"Dry Run: {dry_run}")
        print("=" * 60)

        # 1. 同步一级事件类型
        first_level_options = await self.sync_first_level(
            page_name=page_name,
            group_name=group_name,
            class_name=class_name,
            dry_run=dry_run,
        )

        if not first_level_options:
            print("\n⚠️ 没有一级事件类型，同步结束")
            return

        # 2. 同步二三级事件类型
        await self.sync_second_third_level(
            page_name=page_name,
            group_name=group_name,
            first_level_options=first_level_options,
            class_name=class_name,
            dry_run=dry_run,
        )

        print("=" * 60)
        print("同步完成!")
        print("=" * 60)


async def main():
    parser = argparse.ArgumentParser(
        description="400电话事件类型数据同步脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 基本用法
    python scripts/sync_400_event_types.py --api-key "af_xxx"

    # 指定页面和字段组
    python scripts/sync_400_event_types.py --api-key "af_xxx" --page-name "用户信息页" --group-name "default"

    # 只打印日志，不实际创建
    python scripts/sync_400_event_types.py --api-key "af_xxx" --dry-run

    # 指定API地址
    python scripts/sync_400_event_types.py --api-key "af_xxx" --base-url "http://localhost:9999"
        """,
    )

    parser.add_argument(
        "--api-key",
        required=True,
        help="API Key (格式: af_xxx)",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:9999",
        help="API基础地址 (默认: http://localhost:9999)",
    )
    parser.add_argument(
        "--class-name",
        default="400电话",
        help="分类名称 (默认: 400电话)",
    )
    parser.add_argument(
        "--page-name",
        default="用户信息页",
        help="页面名称 (默认: 用户信息页)",
    )
    parser.add_argument(
        "--group-name",
        default="default",
        help="字段组名称 (默认: default)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印日志，不实际创建",
    )

    args = parser.parse_args()

    syncer = EventTypeSyncer(
        api_key=args.api_key,
        base_url=args.base_url,
    )

    try:
        await syncer.sync(
            page_name=args.page_name,
            group_name=args.group_name,
            class_name=args.class_name,
            dry_run=args.dry_run,
        )
    except Exception as e:
        print(f"\n❌ 错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
