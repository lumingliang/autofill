#!/usr/bin/env python3
"""
同步下拉选项到字段明细的脚本

功能：
1. 调用 A1 接口获取所有一级菜单
2. 为每个一级菜单创建一个字段（一级字段），选项为所有一级菜单的值
3. 遍历每个一级菜单，调用 A2 接口获取二三级菜单
4. 为每个一级菜单创建一个二三级字段，选项为二三级菜单的扁平化值（用 - 连接）

使用方法：
    python scripts/sync_dropdown_to_fields.py --api-key "your_api_key" --field-group-id 123 --class-name "your_class_name"

参数：
    --api-key: API Key（必需）
    --base-url: API 基础地址，默认 http://localhost:9999
    --field-group-id: 字段组ID（必需）
    --class-name: 分类名称（可选）
    --first-level-field-name: 一级字段名称，默认 "first_level_menu"
    --dry-run: 只打印日志，不实际创建字段
"""

import argparse
import asyncio
import sys
from typing import Any, Dict, List, Optional

import httpx


class DropdownToFieldSyncer:
    """下拉选项同步到字段的同步器"""

    def __init__(self, api_key: str, base_url: str = "http://localhost:9999"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """发送 HTTP 请求"""
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

    async def get_first_level_menus(self, class_name: str = "") -> List[Dict]:
        """
        A1. 获取所有一级菜单

        Args:
            class_name: 分类名称（可选）

        Returns:
            一级菜单列表
        """
        params = {}
        if class_name:
            params["class_name"] = class_name

        result = await self._request(
            "GET",
            "/api/public/autofill/dropdown/first_level",
            params=params,
        )

        if result.get("code") != 200:
            raise Exception(f"获取一级菜单失败: {result.get('msg')}")

        return result.get("data", [])

    async def get_submenus_tree(
        self, first_level_value: str, class_name: str = ""
    ) -> Dict:
        """
        A2. 获取二三级菜单树形结构

        Args:
            first_level_value: 一级菜单选项值
            class_name: 分类名称（可选）

        Returns:
            树形结构数据
        """
        params = {"first_level_value": first_level_value}
        if class_name:
            params["class_name"] = class_name

        result = await self._request(
            "GET",
            "/api/public/autofill/dropdown/submenus_tree",
            params=params,
        )

        if result.get("code") != 200:
            raise Exception(f"获取二三级菜单失败: {result.get('msg')}")

        return result.get("data", {})

    async def create_field_spec(
        self,
        field_group_id: int,
        field_name: str,
        field_label: str,
        options: List[Dict],
        field_type: str = "select",
        fill_instruction: str = "",
    ) -> Dict:
        """
        创建字段明细

        Args:
            field_group_id: 字段组ID
            field_name: 字段名
            field_label: 字段显示名称
            options: 选项列表
            field_type: 字段类型
            fill_instruction: 填写指引

        Returns:
            创建的字段信息
        """
        json_data = {
            "field_group_id": field_group_id,
            "field_name": field_name,
            "field_label": field_label,
            "field_type": field_type,
            "fill_instruction": fill_instruction,
            "options": {
                "source": "static",
                "items": options,
            },
        }

        result = await self._request(
            "POST",
            "/api/public/autofill/field_spec/create",
            json_data=json_data,
        )

        if result.get("code") != 200:
            raise Exception(f"创建字段失败: {result.get('msg')}")

        return result.get("data", {})

    def flatten_tree(
        self, tree: List[Dict], parent_value: str = "", separator: str = " - "
    ) -> List[Dict]:
        """
        将树形结构扁平化为选项列表

        Args:
            tree: 树形数据
            parent_value: 父级值
            separator: 分隔符

        Returns:
            扁平化的选项列表
        """
        result = []
        for node in tree:
            current_value = node.get("option_value", "")
            full_value = (
                f"{parent_value}{separator}{current_value}"
                if parent_value
                else current_value
            )

            # 如果有子级，递归处理
            children = node.get("children", [])
            if children:
                result.extend(self.flatten_tree(children, full_value, separator))
            else:
                # 叶子节点，添加到结果
                result.append({
                    "value": full_value,
                    "label": full_value,
                    "base_annotation": node.get("summary", ""),
                })

        return result

    async def sync(
        self,
        field_group_id: int,
        class_name: str = "",
        first_level_field_name: str = "first_level_menu",
        dry_run: bool = False,
    ):
        """
        执行同步操作

        Args:
            field_group_id: 字段组ID
            class_name: 分类名称
            first_level_field_name: 一级字段名称
            dry_run: 是否只打印日志
        """
        print(f"开始同步下拉选项到字段...")
        print(f"字段组ID: {field_group_id}")
        print(f"分类名称: {class_name or '(未指定)'}")
        print(f"一级字段名称: {first_level_field_name}")
        print(f"Dry Run: {dry_run}")
        print("-" * 50)

        # 1. 获取所有一级菜单
        print("\n[步骤1] 获取所有一级菜单...")
        first_level_menus = await self.get_first_level_menus(class_name)
        print(f"获取到 {len(first_level_menus)} 个一级菜单")

        if not first_level_menus:
            print("没有一级菜单数据，同步结束")
            return

        # 打印一级菜单
        for menu in first_level_menus:
            print(f"  - {menu.get('option_value')} (ID: {menu.get('id')})")

        # 2. 创建一级字段
        print(f"\n[步骤2] 创建一级字段: {first_level_field_name}")
        first_level_options = [
            {
                "value": menu.get("option_value", ""),
                "label": menu.get("option_value", ""),
                "base_annotation": menu.get("summary", ""),
            }
            for menu in first_level_menus
        ]

        if dry_run:
            print(f"  [Dry Run] 将创建一级字段，选项数量: {len(first_level_options)}")
        else:
            try:
                field = await self.create_field_spec(
                    field_group_id=field_group_id,
                    field_name=first_level_field_name,
                    field_label="一级菜单",
                    options=first_level_options,
                    fill_instruction="请选择一级菜单",
                )
                print(f"  创建成功: {field.get('field_name')} (ID: {field.get('id')})")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"  字段已存在，跳过: {first_level_field_name}")
                else:
                    raise

        # 3. 遍历每个一级菜单，创建二三级字段
        print(f"\n[步骤3] 为每个一级菜单创建二三级字段...")

        for menu in first_level_menus:
            option_value = menu.get("option_value", "")
            menu_id = menu.get("id")

            print(f"\n  处理一级菜单: {option_value}")

            # 获取二三级菜单
            try:
                tree_data = await self.get_submenus_tree(option_value, class_name)
            except Exception as e:
                print(f"    获取二三级菜单失败: {e}")
                continue

            children = tree_data.get("children", [])
            if not children:
                print(f"    没有二三级菜单，跳过")
                continue

            print(f"    获取到 {len(children)} 个二级菜单")

            # 扁平化树形结构
            flat_options = self.flatten_tree(children, option_value)
            print(f"    扁平化后选项数量: {len(flat_options)}")

            if not flat_options:
                print(f"    没有有效的选项，跳过")
                continue

            # 生成字段名（使用一级菜单值的安全版本）
            safe_field_name = self._sanitize_field_name(option_value)
            sub_field_name = f"{first_level_field_name}_{safe_field_name}"

            print(f"    将创建字段: {sub_field_name}")

            if dry_run:
                print(f"    [Dry Run] 选项示例:")
                for opt in flat_options[:3]:
                    print(f"      - {opt['value']}")
                if len(flat_options) > 3:
                    print(f"      ... 还有 {len(flat_options) - 3} 个选项")
            else:
                try:
                    field = await self.create_field_spec(
                        field_group_id=field_group_id,
                        field_name=sub_field_name,
                        field_label=f"{option_value} - 子菜单",
                        options=flat_options,
                        fill_instruction=f"请选择 {option_value} 的子菜单",
                    )
                    print(f"    创建成功: {field.get('field_name')} (ID: {field.get('id')})")
                except Exception as e:
                    if "already exists" in str(e):
                        print(f"    字段已存在，跳过: {sub_field_name}")
                    else:
                        print(f"    创建失败: {e}")

        print("\n" + "=" * 50)
        print("同步完成!")

    def _sanitize_field_name(self, name: str) -> str:
        """
        将字符串转换为安全的字段名

        Args:
            name: 原始名称

        Returns:
            安全的字段名
        """
        # 替换特殊字符
        safe = name.replace(" ", "_").replace("-", "_").replace("/", "_")
        safe = safe.replace("\\", "_").replace(".", "_").replace(",", "_")
        # 只保留字母、数字和下划线
        safe = "".join(c for c in safe if c.isalnum() or c == "_")
        # 确保以字母开头
        if safe and safe[0].isdigit():
            safe = "_" + safe
        # 转换为小写
        safe = safe.lower()
        return safe[:64]  # 限制长度


async def main():
    parser = argparse.ArgumentParser(
        description="同步下拉选项到字段明细",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 基本用法
    python scripts/sync_dropdown_to_fields.py --api-key "af_xxx" --field-group-id 123

    # 指定分类名称
    python scripts/sync_dropdown_to_fields.py --api-key "af_xxx" --field-group-id 123 --class-name "menu_category"

    # 只打印日志，不实际创建
    python scripts/sync_dropdown_to_fields.py --api-key "af_xxx" --field-group-id 123 --dry-run
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
        help="API 基础地址 (默认: http://localhost:9999)",
    )
    parser.add_argument(
        "--field-group-id",
        type=int,
        required=True,
        help="字段组ID",
    )
    parser.add_argument(
        "--class-name",
        default="",
        help="分类名称（可选）",
    )
    parser.add_argument(
        "--first-level-field-name",
        default="first_level_menu",
        help="一级字段名称 (默认: first_level_menu)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印日志，不实际创建字段",
    )

    args = parser.parse_args()

    syncer = DropdownToFieldSyncer(
        api_key=args.api_key,
        base_url=args.base_url,
    )

    try:
        await syncer.sync(
            field_group_id=args.field_group_id,
            class_name=args.class_name,
            first_level_field_name=args.first_level_field_name,
            dry_run=args.dry_run,
        )
    except Exception as e:
        print(f"\n错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
