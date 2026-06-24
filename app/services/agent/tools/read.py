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
    limit: int = Field(ge=1, le=1000, description=(
        "The number of lines to read (must be at least 1, cannot be negative). This\n"
        "parameter is required and controls how many lines to read from the file."
    ))
    offset: Optional[int] = Field(default=None, ge=1, description=(
        "The line number to start reading from (must be at least 1). Only provide if the\n"
        "file is too large to read at once."
    ))


async def execute_read(file_path: str, limit: int, offset: Optional[int] = None) -> str:
    """读取文件内容并返回带行号范围的结果。"""
    try:
        if not os.path.exists(file_path):
            return format_tool_result("error", f"File not found: {file_path}", is_json=False)

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total_lines = len(lines)
        start = (offset - 1) if offset else 0
        end = start + limit
        selected_lines = lines[start:end]

        actual_end = start + len(selected_lines)
        start_line = start + 1

        content = "".join(selected_lines)

        # 超过 20KB 时截断，避免消息过大
        size_limit = 20 * 1024
        truncated_prefix = ""
        if len(content.encode('utf-8')) > size_limit:
            truncated_prefix = "File content truncated due to size limit (20KB). First 20KB included below:\n\n"
            content = content.encode('utf-8')[:size_limit].decode('utf-8', errors='ignore')

        result = f"{truncated_prefix}Content from line {start_line} to line {actual_end}:\n{content}"
        return format_tool_result("done", result, is_json=False)
    except Exception as e:
        return format_tool_result("error", str(e), is_json=False)


def get_read_tool() -> BaseTool:
    return StructuredTool.from_function(
        name="Read",
        description=(
            "Reads a file from the local filesystem. You can access any file directly by\n"
            "using this tool.\n"
            "Assume this tool is able to read all files on the machine. If the User provides\n"
            "a path to a file assume that path is valid. It is okay to read a file that does\n"
            "not exist; an error will be returned.\n"
            "\n"
            "Usage:\n"
            "  - The file_path parameter must be an absolute path, not a relative path\n"
            "  - You can optionally specify a line offset and limit (especially handy for\n"
            "long files)\n"
            "  - Results are returned using cat -n format, with line numbers starting at 1\n"
            "  -  When you already know which part of the file you need, only read that part.\n"
            "This can be important for larger files.\n"
            "  - You have the capability to call multiple tools in a single response. It is\n"
            "always better to speculatively read multiple files as a batch that are\n"
            "potentially useful.\n"
            "  - If you read a file that exists but has empty contents you will receive a\n"
            "system reminder warning in place of file contents.\n"
        ),
        func=None,
        coroutine=execute_read,
        args_schema=ReadInput,
    )
