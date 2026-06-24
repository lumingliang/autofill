"""
工具执行辅助模块

保留工具结果格式化等公共辅助函数，不再承担工具路由职责。
"""
import json
from typing import Any


def format_tool_result(status: str, result: Any, is_json: bool = True) -> str:
    """格式化工具执行结果为 XML 标签格式。"""
    if is_json and isinstance(result, dict):
        result_str = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        result_str = str(result)

    return f"""<toolcall_status>{status}</toolcall_status>
<toolcall_result>
{result_str}
</toolcall_result>"""


def format_todo_write_result(status: str, todos: list[dict[str, Any]]) -> str:
    """格式化 TodoWrite 工具执行结果，包含 system-reminder。"""
    todos_json = json.dumps(todos, ensure_ascii=False)

    return f"""<toolcall_status>{status}</toolcall_status>
<toolcall_result>
Todos have been modified successfully. Ensure that you continue to use the todo list to track your progress. Please proceed with the current tasks if applicable

<system-reminder>
Your todo list has changed. DO NOT mention this explicitly to the user. Here are the latest contents of your todo list:

{{"todos":{todos_json}}}
</system-reminder>
</toolcall_result>"""
