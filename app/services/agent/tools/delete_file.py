"""
DeleteFile 工具 - 删除文件
"""
import os
from typing import List

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from app.services.agent.tool_executor import format_tool_result


class DeleteFileInput(BaseModel):
    file_paths: List[str] = Field(description=(
        "The list of file paths you want to delete, you MUST set file path to absolute\n"
        "path."
    ))


async def execute_delete_file(file_paths: List[str]) -> str:
    try:
        deleted = []
        errors = []
        for file_path in file_paths:
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted.append(file_path)
            else:
                errors.append(f"File not found: {file_path}")

        return format_tool_result("done", {
            "deleted": deleted,
            "errors": errors
        })
    except Exception as e:
        return format_tool_result("error", {"error": str(e)})


def get_delete_file_tool() -> BaseTool:
    return StructuredTool.from_function(
        name="DeleteFile",
        description=(
            "You can use this tool to delete files, you can delete multi files in one\n"
            "toolcall, and you MUST make sure the files is exist before deleting.\n"
            "When you need to delete file, you MUST use this tool to delete file instead of\n"
            "using shell.\n"
        ),
        func=None,
        coroutine=execute_delete_file,
        args_schema=DeleteFileInput,
    )
