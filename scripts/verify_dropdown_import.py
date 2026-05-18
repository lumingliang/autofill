#!/usr/bin/env python3
"""
验证CSV导入的下拉选项数据是否能通过公开API接口正确获取
- 获取一级菜单列表
- 获取二三级菜单树形结构

使用方法:
    python verify_dropdown_import.py [--api-key API_KEY] [--base-url BASE_URL] [--app-name APP_NAME]

示例:
    python verify_dropdown_import.py
    python verify_dropdown_import.py --api-key af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR --app-name test_app
"""

import argparse
import json
import sys
from typing import Dict, List, Any, Optional

import requests

# 默认配置
DEFAULT_API_BASE_URL = "http://localhost:9999"
DEFAULT_API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
DEFAULT_APP_NAME = "test_app"
DEFAULT_CLASS_NAME = "事件类型"


def make_api_request(
    base_url: str,
    api_key: str,
    endpoint: str,
    data: Dict[str, Any]
) -> Optional[Dict]:
    """发送API请求"""
    url = f"{base_url}/api{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    try:
        print(f"\n  请求: POST {endpoint}")
        print(f"  参数: {json.dumps(data, ensure_ascii=False, indent=2)}")

        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()

        result = response.json()
        print(f"  响应: code={result.get('code')}, msg={result.get('msg')}")
        return result
    except requests.exceptions.RequestException as e:
        print(f"  请求失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  响应状态码: {e.response.status_code}")
            print(f"  响应内容: {e.response.text[:500]}")
        return None


def check_first_level_menus(
    base_url: str,
    api_key: str,
    app_name: str,
    class_name: str
) -> bool:
    """检查一级菜单列表"""
    print(f"\n{'='*60}")
    print(f"检查一级菜单列表")
    print(f"应用: {app_name}, 分类: {class_name}")
    print(f"{'='*60}")

    data = {
        "app_name": app_name,
        "class_name": class_name
    }

    result = make_api_request(base_url, api_key, "/autofill/dropdown/first_level", data)

    if not result:
        print("  结果: 请求失败")
        return False

    if result.get("code") != 200:
        print(f"  结果: 失败 - {result.get('msg')}")
        return False

    menus = result.get("data", [])
    if not menus:
        print("  结果: 未找到任何一级菜单")
        return False

    print(f"\n  找到 {len(menus)} 个一级菜单:")
    for menu in menus:
        print(f"    - ID: {menu.get('id')}, 编码: {menu.get('option_value')}, 标签: {menu.get('summary')}")

    print(f"\n  结果: 成功")
    return True


def check_submenus_tree(
    base_url: str,
    api_key: str,
    app_name: str,
    class_name: str,
    first_level_value: str
) -> bool:
    """检查二三级菜单树形结构"""
    print(f"\n{'='*60}")
    print(f"检查二三级菜单树形结构")
    print(f"应用: {app_name}, 分类: {class_name}, 一级菜单: {first_level_value}")
    print(f"{'='*60}")

    data = {
        "app_name": app_name,
        "class_name": class_name,
        "first_level_value": first_level_value
    }

    result = make_api_request(base_url, api_key, "/autofill/dropdown/submenus_tree", data)

    if not result:
        print("  结果: 请求失败")
        return False

    if result.get("code") != 200:
        print(f"  结果: 失败 - {result.get('msg')}")
        return False

    tree_data = result.get("data", {})
    first_level = tree_data.get("first_level", {})
    children = tree_data.get("children", [])

    print(f"\n  一级菜单:")
    print(f"    - ID: {first_level.get('id')}")
    print(f"    - 编码: {first_level.get('option_value')}")
    print(f"    - 标签: {first_level.get('summary')}")

    if not children:
        print(f"\n  二级菜单: 无")
    else:
        print(f"\n  二级菜单 ({len(children)} 个):")
        for child in children:
            print(f"    - 编码: {child.get('option_value')}, 标签: {child.get('summary')}")

            # 打印三级菜单
            grandchildren = child.get("children", [])
            if grandchildren:
                print(f"      三级菜单 ({len(grandchildren)} 个):")
                for grandchild in grandchildren:
                    print(f"        - 编码: {grandchild.get('option_value')}, 标签: {grandchild.get('summary')}")
            else:
                print(f"      三级菜单: 无")

    print(f"\n  结果: 成功")
    return True


def main():
    parser = argparse.ArgumentParser(description="验证下拉选项导入数据")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API Key")
    parser.add_argument("--base-url", default=DEFAULT_API_BASE_URL, help="API基础URL")
    parser.add_argument("--app-name", default=DEFAULT_APP_NAME, help="应用名称")
    parser.add_argument("--class-name", default=DEFAULT_CLASS_NAME, help="分类名称")
    parser.add_argument("--first-level", help="指定一级菜单编码（可选，不指定则自动获取第一个）")

    args = parser.parse_args()

    print(f"\n{'#'*60}")
    print(f"# 开始验证下拉选项导入数据")
    print(f"# API: {args.base_url}")
    print(f"# 应用: {args.app_name}")
    print(f"# 分类: {args.class_name}")
    print(f"{'#'*60}")

    all_passed = True

    # 1. 检查一级菜单
    if not check_first_level_menus(args.base_url, args.api_key, args.app_name, args.class_name):
        all_passed = False

    # 2. 检查二三级菜单树
    # 如果指定了一级菜单，直接使用；否则需要先从一级列表获取
    first_level_value = args.first_level
    if not first_level_value:
        # 先获取一级菜单列表
        result = make_api_request(
            args.base_url, args.api_key,
            "/autofill/dropdown/first_level",
            {"app_name": args.app_name, "class_name": args.class_name}
        )
        if result and result.get("code") == 200:
            menus = result.get("data", [])
            if menus:
                first_level_value = menus[0].get("option_value")
                print(f"\n  自动选择第一个一级菜单: {first_level_value}")
            else:
                print("\n  未找到一级菜单，跳过二三级菜单检查")
                all_passed = False

    if first_level_value:
        if not check_submenus_tree(
            args.base_url, args.api_key,
            args.app_name, args.class_name,
            first_level_value
        ):
            all_passed = False

    # 总结
    print(f"\n{'#'*60}")
    if all_passed:
        print("# 验证结果: 全部通过")
    else:
        print("# 验证结果: 存在失败项")
    print(f"{'#'*60}\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
