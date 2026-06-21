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


async def execute_ls(path: str, ignore: Optional[List[str]] = None) -> str:
    """执行 LS 工具 - 与 1.json 一致"""
    try:
        items = []
        for item in os.listdir(path):
            # 检查是否被忽略
            if ignore:
                skip = False
                for pattern in ignore:
                    if fnmatch.fnmatch(item, pattern):
                        skip = True
                        break
                if skip:
                    continue

            full_path = os.path.join(path, item)
            items.append({
                "name": item,
                "path": full_path,
                "type": "directory" if os.path.isdir(full_path) else "file"
            })

        return format_tool_result("done", {
            "path": path,
            "items": items
        })
    except Exception as e:
        return format_tool_result("error", {"error": str(e)})


def get_ls_tool() -> BaseTool:
    return StructuredTool.from_function(
        name="LS",
        description="Lists files and directories in a given path.\nThe path parameter must be an absolute path, not a relative path.\nYou can optionally provide an array of glob patterns to ignore with the ignore\nparameter.\n",
        func=None,
        coroutine=execute_ls,
        args_schema=LSInput,
    )
