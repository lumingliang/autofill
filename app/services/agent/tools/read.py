"""
Read 工具 - 读取文件
"""
import os
from typing import Optional

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from app.services.agent.tool_executor import format_tool_result


class ReadInput(BaseModel):
    file_path: str = Field(description="The absolute path to the file to read.")
    limit: int = Field(ge=1, le=1000, description="The number of lines to read (must be at least 1, cannot be negative). This parameter is required and controls how many lines to read from the file.")
    offset: Optional[int] = Field(default=None, ge=1, description="The line number to start reading from (must be at least 1). Only provide if the file is too large to read at once.")


async def execute_read(file_path: str, limit: int, offset: Optional[int] = None) -> str:
    """执行 Read 工具 - 与 1.json 一致

    返回文件内容（文本格式），与 cat -n 格式一致
    """
    try:
        if not os.path.exists(file_path):
            return format_tool_result("error", f"File not found: {file_path}", is_json=False)

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        start = (offset - 1) if offset else 0
        end = start + limit
        selected_lines = lines[start:end]

        # 添加行号，与 cat -n 格式一致
        content = "".join(f"{start + i + 1:6}\t{line}" for i, line in enumerate(selected_lines))

        # 返回纯文本内容
        return format_tool_result("done", content, is_json=False)
    except Exception as e:
        return format_tool_result("error", str(e), is_json=False)


def get_read_tool() -> BaseTool:
    return StructuredTool.from_function(
        name="Read",
        description="Reads a file from the local filesystem. You can access any file directly by using this tool.\nAssume this tool is able to read all files on the machine. If the User provides a path to a file assume that path is valid. It is okay to read a file that does not exist; an error will be returned.\n\nUsage:\n  - The file_path parameter must be an absolute path, not a relative path\n  - You can optionally specify a line offset and limit (especially handy for long files)\n  - Results are returned using cat -n format, with line numbers starting at 1\n  -  When you already know which part of the file you need, only read that part. This can be important for larger files.\n  - You have the capability to call multiple tools in a single response. It is always better to speculatively read multiple files as a batch that are potentially useful.\n  - If you read a file that exists but has empty contents you will receive a system reminder warning in place of file contents.\n",
        func=None,
        coroutine=execute_read,
        args_schema=ReadInput,
    )
