"""
Write 工具 - 写入文件
"""
import os
from typing import Optional

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, ConfigDict, Field

from app.services.agent.tool_executor import format_tool_result


class WriteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_path: str = Field(description="The absolute path to the file to write (must be absolute, not relative)")
    content: str = Field(description="The content to write to the file")


async def execute_write(file_path: str, content: str) -> str:
    """执行 Write 工具 - 与 1.json 一致"""
    try:
        parent_dir = os.path.dirname(file_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return format_tool_result("done", {
            "file_path": file_path,
            "status": "written"
        })
    except Exception as e:
        return format_tool_result("error", {"error": str(e)})


def get_write_tool() -> BaseTool:
    return StructuredTool.from_function(
        name="Write",
        description="Writes a file to the local filesystem.\n\nUsage:\n- This tool will overwrite the existing file if there is one at the provided path.\n- If this is an existing file, you MUST use the Read tool first to read the file's contents. This tool will fail if you did not read the file first.\n- ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.\n- NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.\n- Only use emojis if the user explicitly requests it. Avoid writing emojis to files unless asked.\n",
        func=None,
        coroutine=execute_write,
        args_schema=WriteInput,
    )
