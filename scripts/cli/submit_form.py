#!/usr/bin/env python3
"""
CLI 脚本：提交表单数据

用法：
    python submit_form.py JSON_DATA [--app_id APP_ID]

参数：
    JSON_DATA    表单数据（JSON格式字符串）
    --app_id     应用ID（可选，默认default）
    --format     输出格式：json/table（默认json）

JSON_DATA 格式：
    {
        "event_type_level1": "EVT001",
        "event_type_level2": "EVT001001",
        "event_type_level3": "EVT001001001",
        "service_summary": "服务记录总结内容"
    }

示例：
    python submit_form.py '{"event_type_level1":"EVT001","event_type_level2":"EVT001001","event_type_level3":"EVT001001001","service_summary":"【客户信息】张三..."}'
"""

import argparse
import json
import requests
from typing import Optional, Dict, Any

# API 配置
API_BASE_URL = "http://127.0.0.1:6666"


def submit_form(data: Dict[str, Any], app_id: Optional[str] = None) -> dict:
    """
    提交表单数据

    参数:
        data: 表单数据字典
        app_id: 应用ID（可选）

    返回:
        提交结果
    """
    url = f"{API_BASE_URL}/api/form/submit"
    payload = {
        "app_id": app_id or "default",
        "data": data
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
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


def format_submit_result(data: dict) -> str:
    """格式化提交结果输出"""
    if data.get("code") != 200:
        return f"错误: {data.get('msg', 'Unknown error')}"

    result = data.get("data", {})
    if not result:
        return "提交失败：无返回数据"

    lines = []
    lines.append("=" * 80)
    lines.append(f"表单提交成功！")
    lines.append("=" * 80)
    lines.append(f"\n【提交信息】")
    lines.append(f"  表单ID: {result.get('form_id', '')}")
    lines.append(f"  应用ID: {result.get('app_id', '')}")
    lines.append(f"  提交时间: {result.get('submitted_at', '')}")
    lines.append(f"  字段数量: {result.get('field_count', 0)}")

    summary = result.get("summary", {})
    if summary:
        lines.append(f"\n【数据摘要】")
        lines.append(f"  事件类型: {summary.get('event_type', '')}")
        lines.append(f"  总结长度: {summary.get('service_summary_length', 0)} 字符")

    lines.append("\n" + "=" * 80)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="提交表单数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用JSON数据提交
  %(prog)s '{"event_type_level1":"EVT001","event_type_level2":"EVT001001","event_type_level3":"EVT001001001","service_summary":"【客户信息】张三..."}'

  # 指定应用ID
  %(prog)s '{"event_type_level1":"EVT001","event_type_level2":"EVT001001","event_type_level3":"EVT001001001","service_summary":"..."}' --app_id app_001

  # 表格格式输出
  %(prog)s '{"event_type_level1":"EVT001","event_type_level2":"EVT001001","event_type_level3":"EVT001001001","service_summary":"..."}' --format table
        """
    )

    parser.add_argument(
        "json_data",
        type=str,
        help="表单数据（JSON格式字符串）"
    )
    parser.add_argument(
        "--app_id",
        type=str,
        default=None,
        help="应用ID（可选，默认default）"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "table"],
        default="json",
        help="输出格式：json/table（默认json）"
    )

    args = parser.parse_args()

    # 解析JSON数据
    try:
        form_data = json.loads(args.json_data)
    except json.JSONDecodeError as e:
        print(f"错误: JSON数据格式不正确 - {e}")
        return 1

    # 验证必需字段
    required_fields = ["event_type_level1", "event_type_level2", "event_type_level3", "service_summary"]
    missing_fields = [f for f in required_fields if f not in form_data]
    if missing_fields:
        print(f"错误: 缺少必需字段 - {', '.join(missing_fields)}")
        return 1

    # 提交表单
    result = submit_form(form_data, args.app_id)

    # 输出结果
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_submit_result(result))

    # 返回退出码
    return 0 if result.get("code") == 200 else 1


if __name__ == "__main__":
    exit(main())
