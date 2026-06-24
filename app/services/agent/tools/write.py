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
    """写入文件内容，覆盖或新建文件并返回变更描述。"""
    try:
        parent_dir = os.path.dirname(file_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        old_content = ""
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                old_content = f.read()

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        if old_content:
            from app.services.agent.tools.search_replace import _format_file_changes
            changes = _format_file_changes(file_path, old_content, content)
        else:
            changes = f"""<file_changes>
The toolcall created the file `{file_path}`:
```
{content}
```
</file_changes>"""

        return format_tool_result("done", changes, is_json=False)
    except Exception as e:
        return format_tool_result("error", {"error": str(e)})


def get_write_tool() -> BaseTool:
    return StructuredTool.from_function(
        name="Write",
        description=(
            "Writes a file to the local filesystem.\n"
            "\n"
            "Usage:\n"
            "- This tool will overwrite the existing file if there is one at the provided\n"
            "path.\n"
            "- If this is an existing file, you MUST use the Read tool first to read the\n"
            "file's contents. This tool will fail if you did not read the file first.\n"
            "- ALWAYS prefer editing existing files in the codebase. NEVER write new files\n"
            "unless explicitly required.\n"
            "- NEVER proactively create documentation files (*.md) or README files. Only\n"
            "create documentation files if explicitly requested by the User.\n"
            "- Only use emojis if the user explicitly requests it. Avoid writing emojis to\n"
            "files unless asked.\n"
        ),
        func=None,
        coroutine=execute_write,
        args_schema=WriteInput,
    )
