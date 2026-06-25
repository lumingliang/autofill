"""
LS 工具 - 列出目录内容
"""
import fnmatch
import os
from typing import List, Optional

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from app.services.agent.tool_executor import format_tool_result


class LSInput(BaseModel):
    path: str = Field(description="The absolute path to the directory to list (must be absolute, not relative).")
    ignore: Optional[List[str]] = Field(default=None, description="List of glob patterns to ignore.")


# 默认忽略的常见噪声目录/文件，与 IDE LS 工具保持一致
DEFAULT_IGNORE_PATTERNS = [
    ".git",
    ".DS_Store",
    ".pytest_cache",
    "__pycache__",
    "*.pyc",
    "node_modules",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
]

# 目录树最大输出行数，超过则截断并提示大模型
MAX_TREE_LINES = 500


def _build_tree(
    path: str,
    prefix: str = "",
    ignore: Optional[List[str]] = None,
    max_lines: int = MAX_TREE_LINES,
    _lines: Optional[List[str]] = None,
) -> str:
    """递归构建目录树文本，与 IDE LS 工具格式保持一致：每级缩进 2 个空格。"""
    if _lines is None:
        _lines = []

    # 根节点显示完整路径并保留目录尾部的 /，子节点显示 basename
    if prefix == "":
        name = path if path.endswith("/") else path + "/"
    else:
        name = os.path.basename(path) or path
    _lines.append(f"{prefix}- {name}")

    if len(_lines) >= max_lines:
        _lines.append(
            f"{prefix}... （结果已截断，仅显示前 {max_lines} 行，建议缩小目录范围或使用 Glob/Grep 精确查找）"
        )
        return "\n".join(_lines)

    if os.path.isdir(path):
        try:
            items = sorted(os.listdir(path))
        except OSError:
            items = []

        all_patterns = list(ignore or [])
        filtered = [
            item for item in items
            if not any(fnmatch.fnmatch(item, p) for p in all_patterns)
        ]

        child_prefix = prefix + "  "
        for item in filtered:
            if len(_lines) >= max_lines:
                _lines.append(
                    f"{prefix}... （结果已截断，仅显示前 {max_lines} 行，建议缩小目录范围或使用 Glob/Grep 精确查找）"
                )
                return "\n".join(_lines)
            full_path = os.path.join(path, item)
            _build_tree(
                full_path,
                child_prefix,
                ignore=all_patterns,
                max_lines=max_lines,
                _lines=_lines,
            )

    return "\n".join(_lines)


async def execute_ls(
    path: str,
    ignore: Optional[List[str]] = None,
) -> str:
    """列出目录内容并返回树形结构。"""
    try:
        if not os.path.exists(path):
            return format_tool_result("error", f"Path not found: {path}", is_json=False)
        if not os.path.isdir(path):
            return format_tool_result("error", f"Not a directory: {path}", is_json=False)

        # 合并默认忽略模式与用户传入的忽略模式
        all_ignore = list(DEFAULT_IGNORE_PATTERNS)
        if ignore:
            all_ignore.extend(ignore)

        tree = _build_tree(path, ignore=all_ignore)
        return format_tool_result("done", tree, is_json=False)
    except Exception as e:
        return format_tool_result("error", str(e), is_json=False)


def get_ls_tool() -> BaseTool:
    return StructuredTool.from_function(
        name="LS",
        description=(
            "Lists files and directories in a given path.\n"
            "The path parameter must be an absolute path, not a relative path.\n"
            "You can optionally provide an array of glob patterns to ignore with the ignore\n"
            "parameter.\n"
            "Common noise directories like .git, __pycache__, node_modules are ignored by default.\n"
            "Output is truncated to a maximum number of lines; if truncated, the result will include a note.\n"
        ),
        func=None,
        coroutine=execute_ls,
        args_schema=LSInput,
    )
