"""
Glob 工具 - 文件模式匹配
"""
import glob as glob_module
import os
from typing import Optional

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from app.services.agent.tool_executor import format_tool_result


class GlobInput(BaseModel):
    pattern: str = Field(description="The glob pattern to match files against.")
    path: Optional[str] = Field(
        default=None,
        description=(
            "The directory to search in. If not specified, the current working directory will\n"
            "be used. Omit this field to use the default directory. DO NOT enter \"undefined\"\n"
            "or \"null\" - simply omit it for the default behavior. Must be a valid absolute\n"
            "directory path if provided."
        )
    )


async def execute_glob(pattern: str, path: Optional[str] = None) -> str:
    search_path = path or os.getcwd()
    full_pattern = os.path.join(search_path, pattern) if not pattern.startswith("/") else pattern

    try:
        files = glob_module.glob(full_pattern, recursive=True)
        files.sort(key=lambda x: os.path.getmtime(x) if os.path.exists(x) else 0, reverse=True)
        files = files[:100]
        if not files:
            return format_tool_result("done", "No matches found", is_json=False)
        return format_tool_result("done", "\n".join(files), is_json=False)
    except Exception as e:
        return format_tool_result("error", str(e), is_json=False)


def get_glob_tool() -> BaseTool:
    return StructuredTool.from_function(
        name="Glob",
        description=(
            "Fast file pattern matching tool that works with any codebase size\n"
            "\n"
            "Usage:\n"
            "  - Supports glob patterns like \"/*.js\" or \"src//*.ts\"\n"
            "  - Returns matching file paths sorted by modification time\n"
            "  - Use this tool when you need to find files by name patterns\n"
            "  - When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the `SearchCodebase` tool instead\n"
            "  - You can call multiple tools in a single response. It is always better to speculatively perform multiple searches in parallel if they are potentially useful.\n"
        ),
        func=None,
        coroutine=execute_glob,
        args_schema=GlobInput,
    )
