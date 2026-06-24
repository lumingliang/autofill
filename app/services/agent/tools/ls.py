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


def _build_tree(path: str, prefix: str = "", ignore: Optional[List[str]] = None) -> str:
    name = os.path.basename(path) or path
    lines = [f"{prefix}- {name}"]
    if os.path.isdir(path):
        try:
            items = sorted(os.listdir(path))
        except OSError:
            items = []
        filtered = []
        for item in items:
            if ignore:
                skip = any(fnmatch.fnmatch(item, p) for p in ignore)
                if skip:
                    continue
            filtered.append(item)
        for idx, item in enumerate(filtered):
            full_path = os.path.join(path, item)
            is_last = idx == len(filtered) - 1
            child_prefix = prefix + ("  " if is_last else "| ")
            lines.append(_build_tree(full_path, child_prefix + " ", ignore=None))
    return "\n".join(lines)


async def execute_ls(path: str, ignore: Optional[List[str]] = None) -> str:
    try:
        if not os.path.exists(path):
            return format_tool_result("error", f"Path not found: {path}", is_json=False)
        if not os.path.isdir(path):
            return format_tool_result("error", f"Not a directory: {path}", is_json=False)

        tree = _build_tree(path, ignore=ignore)
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
        ),
        func=None,
        coroutine=execute_ls,
        args_schema=LSInput,
    )
