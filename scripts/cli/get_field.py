#!/usr/bin/env python3
"""
CLI 脚本：获取表单字段信息

用法：
    # 获取所有字段列表
    python get_field.py
    
    # 获取指定字段的选项（下拉列表）
    python get_field.py event_type_level1
    python get_field.py event_type_level2 --parent_id EVT001
    python get_field.py event_type_level3 --parent_id EVT001001
    
    # 获取模板列表（根据一级事件类型ID）
    python get_field.py service_summary --list_templates EVT001
    
    # 获取模板内容（根据模板ID）
    python get_field.py service_summary --template_id 1

参数：
    field_name          字段名称（可选，不传则获取列表）
    --parent_id         父级选项ID（级联字段查询时使用）
    --list_templates    一级事件类型ID（获取模板列表时使用）
    --template_id       模板ID（获取模板内容时使用）
    --format            输出格式：json/table（默认json）

字段说明：
    - event_type_level1: 一级事件类型（下拉）
    - event_type_level2: 二级事件类型（下拉，级联，需parent_id）
    - event_type_level3: 三级事件类型（下拉，级联，需parent_id）
    - service_summary: 服务记录总结（文本域，需选择模板）
"""

import argparse
import json
import requests
from typing import Optional, Dict, Any

# API 配置
API_BASE_URL = "http://127.0.0.1:6666"


def get_field_list() -> dict:
    """获取表单字段列表"""
    url = f"{API_BASE_URL}/api/form/fields"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {
            "code": 503,
            "msg": f"无法连接到服务 {API_BASE_URL}，请确保服务已启动",
            "data": None
        }
    except requests.exceptions.Timeout:
        return {
            "code": 504,
            "msg": "请求超时",
            "data": None
        }
    except Exception as e:
        return {
            "code": 500,
            "msg": f"请求失败: {str(e)}",
            "data": None
        }


def get_field_options(field_name: str, parent_id: Optional[str] = None) -> dict:
    """
    获取下拉字段的可选值

    参数:
        field_name: 字段ID (event_type_level1 / event_type_level2 / event_type_level3)
        parent_id: 父级选项ID（级联查询时使用）

    返回:
        包含选项列表的响应数据
    """
    url = f"{API_BASE_URL}/api/form/fields/{field_name}/options"
    params = {}
    if parent_id:
        params["parent_id"] = parent_id

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {
            "code": 503,
            "msg": f"无法连接到服务 {API_BASE_URL}，请确保服务已启动",
            "data": None
        }
    except requests.exceptions.Timeout:
        return {
            "code": 504,
            "msg": "请求超时",
            "data": None
        }
    except Exception as e:
        return {
            "code": 500,
            "msg": f"请求失败: {str(e)}",
            "data": None
        }


def get_template_list(level1_id: str) -> dict:
    """
    根据一级事件类型ID获取模板列表

    参数:
        level1_id: 一级事件类型ID（如 EVT001）

    返回:
        包含模板列表的响应数据
    """
    url = f"{API_BASE_URL}/api/templates/list/{level1_id}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {
            "code": 503,
            "msg": f"无法连接到服务 {API_BASE_URL}，请确保服务已启动",
            "data": None
        }
    except requests.exceptions.Timeout:
        return {
            "code": 504,
            "msg": "请求超时",
            "data": None
        }
    except Exception as e:
        return {
            "code": 500,
            "msg": f"请求失败: {str(e)}",
            "data": None
        }


def get_template_content(template_id: str) -> dict:
    """
    获取服务记录模板内容

    参数:
        template_id: 模板ID（如 1, 2, 3...）

    返回:
        包含模板内容的响应数据
    """
    url = f"{API_BASE_URL}/api/templates/{template_id}/content"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {
            "code": 503,
            "msg": f"无法连接到服务 {API_BASE_URL}，请确保服务已启动",
            "data": None
        }
    except requests.exceptions.Timeout:
        return {
            "code": 504,
            "msg": "请求超时",
            "data": None
        }
    except Exception as e:
        return {
            "code": 500,
            "msg": f"请求失败: {str(e)}",
            "data": None
        }


def format_list_output(data: dict) -> str:
    """格式化字段列表输出"""
    if data.get("code") != 200:
        return f"错误: {data.get('msg', 'Unknown error')}"
    
    result_data = data.get("data", {})
    fields = result_data.get("fields", [])
    
    if not fields:
        return "暂无字段数据"
    
    lines = []
    lines.append("=" * 100)
    lines.append(f"{'字段ID':<25}{'字段名称':<20}{'类型':<12}{'必填':<8}{'说明'}")
    lines.append("-" * 100)
    
    for field in fields:
        field_id = field.get("field_id", "")[:23]
        field_name = field.get("field_name", "")[:18]
        field_type = field.get("field_type", "")[:10]
        required = "是" if field.get("required") else "否"
        description = field.get("description", "")[:30]
        
        lines.append(f"{field_id:<25}{field_name:<20}{field_type:<12}{required:<8}{description}")
    
    lines.append("=" * 100)
    lines.append(f"\n总计: {len(fields)} 个字段")
    
    return "\n".join(lines)


def format_options_output(data: dict) -> str:
    """格式化选项列表输出"""
    if data.get("code") != 200:
        return f"错误: {data.get('msg', 'Unknown error')}"

    result_data = data.get("data", {})
    field_id = result_data.get("field_id", "")
    parent_id = result_data.get("parent_id")
    options = result_data.get("options", [])

    if not options:
        return "暂无选项数据"

    lines = []
    lines.append("=" * 100)

    if parent_id:
        lines.append(f"字段ID: {field_id} (父级: {parent_id})")
    else:
        lines.append(f"字段ID: {field_id}")

    lines.append("-" * 100)
    lines.append(f"{'序号':<6}{'选项ID':<20}{'选项名称':<20}{'描述'}")
    lines.append("-" * 100)

    for i, option in enumerate(options, 1):
        option_id = option.get("option_id", "")[:18]
        option_name = option.get("option_name", "")[:18]
        description = option.get("description", "")[:40]

        lines.append(f"{i:<6}{option_id:<20}{option_name:<20}{description}")

    lines.append("=" * 100)
    lines.append(f"\n总计: {len(options)} 个选项")

    return "\n".join(lines)


def format_template_list_output(data: dict) -> str:
    """格式化模板列表输出"""
    if data.get("code") != 200:
        return f"错误: {data.get('msg', 'Unknown error')}"

    result_data = data.get("data", {})
    level1_id = result_data.get("level1_id", "")
    templates = result_data.get("templates", [])

    lines = []
    lines.append("=" * 100)
    lines.append(f"模板列表 (一级事件类型: {level1_id})")
    lines.append("=" * 100)

    if not templates:
        lines.append("\n暂无可用模板")
    else:
        lines.append(f"\n{'序号':<6}{'模板ID':<12}{'模板名称':<25}{'变量数':<8}{'说明'}")
        lines.append("-" * 100)
        for i, template in enumerate(templates, 1):
            template_id = template.get("template_id", "")[:10]
            template_name = template.get("template_name", "")[:23]
            var_count = str(template.get("variable_count", 0))
            summary = template.get("summary", "")[:35]
            lines.append(f"{i:<6}{template_id:<12}{template_name:<25}{var_count:<8}{summary}")

    lines.append("\n" + "=" * 100)
    lines.append(f"\n总计: {len(templates)} 个模板")

    return "\n".join(lines)


def format_template_content_output(data: dict) -> str:
    """格式化模板内容输出"""
    if data.get("code") != 200:
        return f"错误: {data.get('msg', 'Unknown error')}"

    result_data = data.get("data", {})
    template_id = result_data.get("template_id", "")
    template_name = result_data.get("template_name", "")
    template_content = result_data.get("template_content", "")
    variables = result_data.get("variables", [])

    lines = []
    lines.append("=" * 100)
    lines.append(f"模板内容: {template_name} (ID: {template_id})")
    lines.append("=" * 100)

    lines.append("\n【模板内容】")
    lines.append(template_content)

    if variables:
        lines.append("\n【模板变量】")
        lines.append(f"{'变量名':<30}{'描述':<30}{'必需':<8}")
        lines.append("-" * 70)
        for var in variables:
            var_name = var.get("name", "")[:28]
            var_desc = var.get("description", "")[:28]
            var_required = "是" if var.get("required") else "否"
            lines.append(f"${var_name:<30}{var_desc:<30}{var_required:<8}")

    lines.append("\n" + "=" * 100)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="获取表单字段信息",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 获取字段列表
  %(prog)s

  # 获取一级事件类型选项
  %(prog)s event_type_level1

  # 获取二级事件类型选项（需要指定parent_id）
  %(prog)s event_type_level2 --parent_id EVT001

  # 获取三级事件类型选项
  %(prog)s event_type_level3 --parent_id EVT001001

  # 获取模板列表（根据一级事件类型ID）
  %(prog)s service_summary --list_templates EVT001

  # 获取模板内容（根据模板ID）
  %(prog)s service_summary --template_id 1

  # 表格格式输出
  %(prog)s --format table
  %(prog)s event_type_level1 --format table
        """
    )
    
    parser.add_argument(
        "field_name",
        type=str,
        nargs="?",
        default=None,
        help="字段名称（如 event_type_level1, event_type_level2, event_type_level3, service_summary），不传则获取列表"
    )
    parser.add_argument(
        "--parent_id",
        type=str,
        default=None,
        help="父级选项ID（查询 event_type_level2 或 event_type_level3 时必填）"
    )
    parser.add_argument(
        "--list_templates",
        type=str,
        default=None,
        help="一级事件类型ID（查询 service_summary 模板列表时使用，如 EVT001）"
    )
    parser.add_argument(
        "--template_id",
        type=str,
        default=None,
        help="模板ID（查询 service_summary 模板内容时使用，如 1, 2, 3...）"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "table"],
        default="json",
        help="输出格式：json/table（默认json）"
    )
    
    args = parser.parse_args()
    
    # 级联字段验证
    if args.field_name in ["event_type_level2", "event_type_level3"] and not args.parent_id:
        parser.error(f"查询 {args.field_name} 选项时必须指定 --parent_id 参数")
    
    # 执行操作
    if args.field_name is None:
        # 不传 field_name，获取字段列表
        result = get_field_list()
    elif args.field_name == "service_summary":
        if args.list_templates:
            # 获取模板列表
            result = get_template_list(args.list_templates)
        elif args.template_id:
            # 获取模板内容
            result = get_template_content(args.template_id)
        else:
            parser.error("查询 service_summary 时必须指定 --list_templates 或 --template_id 参数")
    else:
        # 传了 field_name，获取该字段的选项
        result = get_field_options(args.field_name, args.parent_id)
    
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if args.field_name is None:
            print(format_list_output(result))
        elif args.field_name == "service_summary":
            if args.list_templates:
                print(format_template_list_output(result))
            elif args.template_id:
                print(format_template_content_output(result))
        else:
            print(format_options_output(result))
    
    # 返回退出码
    return 0 if result.get("code") == 200 else 1


if __name__ == "__main__":
    exit(main())
