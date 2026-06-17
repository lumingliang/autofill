#!/usr/bin/env python3
"""
CLI 脚本：获取字段填写规则

用法：
    # 获取字段规则（默认返回所有选项的规则）
    python get_field_rules.py event_type_level1
    
    # 获取二级事件类型规则（指定父级，返回该父级下所有子选项的规则）
    python get_field_rules.py event_type_level2 --parent_id EVT001
    
    # 获取单个选项规则
    python get_field_rules.py event_type_level1 EVT001
    
    # 获取模板规则（适用于 service_summary）
    python get_field_rules.py service_summary --template_id 1

参数：
    field_id        字段ID（必填）
    option_id       选项ID（可选，指定后只返回单个选项的规则）
    --parent_id     父级选项ID（可选，级联字段过滤时使用）
    --template_id   模板ID（可选，用于获取模板规则）
    --format        输出格式：json/table（默认json）

字段说明：
    - event_type_level1: 一级事件类型（下拉）
    - event_type_level2: 二级事件类型（下拉，级联）
    - event_type_level3: 三级事件类型（下拉，级联）
    - service_summary: 服务记录总结（文本域，需选择模板）
"""

import argparse
import json
import requests
from typing import Optional

# API 配置
API_BASE_URL = "http://127.0.0.1:6666"


def get_field_rules(field_id: str, option_id: Optional[str] = None, parent_id: Optional[str] = None) -> dict:
    """
    获取字段的填写规则

    参数:
        field_id: 字段ID
        option_id: 选项ID（可选，指定后只返回单个选项的规则）
        parent_id: 父级选项ID（可选，级联字段过滤时使用）

    返回:
        包含字段规则的响应数据
    """
    url = f"{API_BASE_URL}/api/form/fields/{field_id}/rules"
    params = {}
    if option_id:
        params["option_id"] = option_id
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


def get_template_rules(template_id: str) -> dict:
    """
    获取模板的填写规则

    参数:
        template_id: 模板ID（如 1, 2, 3...）

    返回:
        包含模板规则的响应数据
    """
    url = f"{API_BASE_URL}/api/templates/{template_id}/rules"

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


def format_field_rule_output(data: dict) -> str:
    """格式化字段规则输出"""
    if data.get("code") != 200:
        return f"错误: {data.get('msg', 'Unknown error')}"

    rule = data.get("data", {})
    if not rule:
        return "暂无规则数据"

    lines = []
    lines.append("=" * 80)
    lines.append(f"字段规则: {rule.get('field_name', '')} ({rule.get('field_id', '')})")
    lines.append("=" * 80)

    # 基础信息
    lines.append("\n【基础信息】")
    lines.append(f"  字段类型: {rule.get('field_type', '')}")
    lines.append(f"  是否必填: {'是' if rule.get('required') else '否'}")
    lines.append(f"  字段说明: {rule.get('description', '')}")

    # 级联规则
    if "cascade_rule" in rule:
        lines.append("\n【级联规则】")
        lines.append(f"  父级字段: {rule['cascade_rule'].get('parent_field', '')}")
        lines.append(f"  查询顺序: {rule['cascade_rule'].get('query_order', '')}")

    # 长度限制
    if "min_length" in rule:
        lines.append(f"\n【长度限制】")
        lines.append(f"  最小长度: {rule.get('min_length')} 字符")
        lines.append(f"  最大长度: {rule.get('max_length')} 字符")

    # 模板相关
    if rule.get("template_based"):
        lines.append(f"\n【模板信息】")
        lines.append(f"  基于模板: 是")
        lines.append(f"  生成提示: {rule.get('auto_generate_hint', '')}")

    # 验证规则
    if "validation_rules" in rule:
        lines.append(f"\n【验证规则】")
        for i, vrule in enumerate(rule["validation_rules"], 1):
            rule_type = vrule.get("type", "")
            message = vrule.get("message", "")
            value = vrule.get("value", "")
            if value:
                lines.append(f"  {i}. [{rule_type}] {message} (值: {value})")
            else:
                lines.append(f"  {i}. [{rule_type}] {message}")

    # 选项填写说明（当指定了option_id时）
    if "option_fill_instruction" in rule:
        inst = rule.get("option_fill_instruction", {})
        lines.append(f"\n【选项填写说明】")
        lines.append(f"  说明: {inst.get('instruction', '')}")
        lines.append(f"  优先级: {inst.get('priority', '')}")
        lines.append(f"  响应时间: {inst.get('response_time', '')}")
        lines.append(f"  必填字段: {', '.join(inst.get('required_fields', []))}")
        lines.append(f"  关键确认点:")
        for point in inst.get('key_points', []):
            lines.append(f"    - {point}")

    # 所有选项规则（默认返回）
    if "options_rules" in rule:
        options_rules = rule.get("options_rules", [])
        options_count = rule.get("options_count", 0)
        parent_id = rule.get("parent_id")
        
        lines.append(f"\n【选项规则列表】")
        if parent_id:
            lines.append(f"  父级ID: {parent_id}")
        lines.append(f"  选项总数: {options_count}")
        
        if options_rules:
            lines.append(f"\n  {'选项ID':<18}{'选项名称':<20}{'优先级':<10}{'响应时间':<15}")
            lines.append(f"  {'-'*65}")
            for opt in options_rules:
                opt_id = opt.get("option_id", "")[:16]
                opt_name = opt.get("option_name", "")[:18]
                priority = opt.get("fill_instruction", {}).get("priority", "")[:8]
                response_time = opt.get("fill_instruction", {}).get("response_time", "")[:13]
                lines.append(f"  {opt_id:<18}{opt_name:<20}{priority:<10}{response_time:<15}")

    lines.append("=" * 80)

    return "\n".join(lines)


def format_template_rule_output(data: dict) -> str:
    """格式化模板规则输出"""
    if data.get("code") != 200:
        return f"错误: {data.get('msg', 'Unknown error')}"

    rule = data.get("data", {})
    if not rule:
        return "暂无规则数据"

    lines = []
    lines.append("=" * 80)
    lines.append(f"模板规则: {rule.get('template_name', '')} (ID: {rule.get('template_id', '')})")
    lines.append("=" * 80)

    # 基础信息
    lines.append("\n【基础信息】")
    lines.append(f"  模板类型: {rule.get('template_type', '')}")
    lines.append(f"  模板说明: {rule.get('description', '')}")

    # 变量规则
    if "variable_rules" in rule:
        var_rules = rule["variable_rules"]
        lines.append(f"\n【变量规则】")
        lines.append(f"  变量总数: {var_rules.get('total_count', 0)}")
        lines.append(f"  必需变量: {var_rules.get('required_count', 0)}")
        lines.append(f"  可选变量: {var_rules.get('optional_count', 0)}")
        
        variables = var_rules.get('variables', [])
        if variables:
            lines.append(f"\n  变量列表:")
            lines.append(f"  {'变量名':<25}{'描述':<30}{'必需':<8}")
            lines.append(f"  {'-'*65}")
            for var in variables:
                var_name = var.get('name', '')[:23]
                var_desc = var.get('description', '')[:28]
                var_required = '是' if var.get('required') else '否'
                lines.append(f"  ${var_name:<25}{var_desc:<30}{var_required:<8}")

    # 验证规则
    if "validation_rules" in rule:
        lines.append(f"\n【验证规则】")
        for i, vrule in enumerate(rule["validation_rules"], 1):
            rule_type = vrule.get("type", "")
            message = vrule.get("message", "")
            value = vrule.get("value", "")
            if value:
                lines.append(f"  {i}. [{rule_type}] {message} (值: {value})")
            else:
                lines.append(f"  {i}. [{rule_type}] {message}")

    # 填写说明
    if "fill_instruction" in rule:
        inst = rule.get("fill_instruction", {})
        lines.append(f"\n【填写说明】")
        lines.append(f"  {inst.get('description', '')}")
        
        steps = inst.get('steps', [])
        if steps:
            lines.append(f"\n  填写步骤:")
            for i, step in enumerate(steps, 1):
                lines.append(f"    {i}. {step}")
        
        key_points = inst.get('key_points', [])
        if key_points:
            lines.append(f"\n  关键确认点:")
            for point in key_points:
                lines.append(f"    - {point}")

    lines.append("\n" + "=" * 80)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="获取字段填写规则",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 获取字段规则（默认返回所有选项规则）
  %(prog)s event_type_level1
  %(prog)s service_summary

  # 获取二级/三级事件类型规则（指定父级）
  %(prog)s event_type_level2 --parent_id EVT001
  %(prog)s event_type_level3 --parent_id EVT001001

  # 获取单个选项规则
  %(prog)s event_type_level1 EVT001
  %(prog)s event_type_level2 EVT001001

  # 获取模板规则
  %(prog)s service_summary --template_id 1

  # 表格格式输出
  %(prog)s event_type_level1 --format table
        """
    )

    parser.add_argument(
        "field_id",
        type=str,
        help="字段ID（如 event_type_level1, event_type_level2, event_type_level3, service_summary）"
    )
    parser.add_argument(
        "option_id",
        type=str,
        nargs="?",
        default=None,
        help="选项ID（可选，指定后只返回单个选项的规则）"
    )
    parser.add_argument(
        "--parent_id",
        type=str,
        default=None,
        help="父级选项ID（可选，级联字段过滤时使用，如查询二级传一级ID）"
    )
    parser.add_argument(
        "--template_id",
        type=str,
        default=None,
        help="模板ID（可选，用于获取模板规则，如 1, 2, 3...）"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "table"],
        default="json",
        help="输出格式：json/table（默认json）"
    )

    args = parser.parse_args()

    # 执行查询
    if args.field_id == "service_summary" and args.template_id:
        # 获取模板规则
        result = get_template_rules(args.template_id)
    else:
        # 获取字段规则
        result = get_field_rules(args.field_id, args.option_id, args.parent_id)

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if args.field_id == "service_summary" and args.template_id:
            print(format_template_rule_output(result))
        else:
            print(format_field_rule_output(result))

    # 返回退出码
    return 0 if result.get("code") == 200 else 1


if __name__ == "__main__":
    exit(main())
