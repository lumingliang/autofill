"""
SearchReplace 工具 - 编辑文件
"""
import difflib
from typing import Optional

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from app.services.agent.tool_executor import format_tool_result


class SearchReplaceInput(BaseModel):
    file_path: str = Field(description="The file path, you MUST set file path to absolute path.")
    old_str: str = Field(description=(
        "The SEARCH section, a contiguous chunk of lines to search for in the existing\n"
        "source code."
    ))
    new_str: str = Field(description="The REPLACE section, the lines to replace into the source code.")


def _format_file_changes(file_path: str, old_content: str, new_content: str) -> str:
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    if old_lines and not old_lines[-1].endswith("\n"):
        old_lines[-1] += "\n"
    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] += "\n"

    diff = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=file_path,
        tofile=file_path,
        n=3,
    ))
    if len(diff) >= 2 and diff[0].startswith("---") and diff[1].startswith("+++"):
        diff = diff[2:]
    diff_str = "".join(diff)

    return f"""<file_changes>
The toolcall made the following changes to the file `{file_path}`:
```
{diff_str}
```
</file_changes>"""


async def execute_search_replace(file_path: str, old_str: str, new_str: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            old_content = f.read()

        if old_str not in old_content:
            return format_tool_result("error", {
                "error": "old_str not found in file",
                "file_path": file_path
            })

        new_content = old_content.replace(old_str, new_str, 1)

        if new_content == old_content:
            return format_tool_result("error", {
                "error": "REPLACE section must be different from SEARCH section",
                "file_path": file_path
            })

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        changes = _format_file_changes(file_path, old_content, new_content)
        return format_tool_result("done", changes, is_json=False)
    except Exception as e:
        return format_tool_result("error", {"error": str(e)})


def get_search_replace_tool() -> BaseTool:
    return StructuredTool.from_function(
        name="SearchReplace",
        description=(
            "You can use this tool to edit file. You should specify the following arguments\n"
            "before the others: `file_path`\n"
            "\n"
            "When you choose to use this tool to edit a existing file, you MUST follow the\n"
            "*SEARCH/REPLACE* Rules to set the `old_str` and `new_str` parameters:\n"
            "\n"
            "1. The `old_str` is the SEARCH section that should be a contiguous chunk of\n"
            "lines to search for in the existing source code.\n"
            "2. The `new_str` is the REPLACE section that should be lines to replace into the\n"
            "source code.\n"
            "3. The REPLACE section MUST be different from the SEARCH section.\n"
            "\n"
            "This tool will *only* replace the first match occurrence of the SEARCH section.\n"
            "Include enough lines in the SEARCH section to uniquely match the set of lines\n"
            "that need to change.\n"
            "\n"
            "Keep your SEARCH and REPLACE sections concise.\n"
            "Include just the changing lines, and a few surrounding lines if needed for\n"
            "uniqueness.\n"
            "Do not include long runs of unchanging lines in your SEARCH and REPLACE\n"
            "sections.\n"
            "\n"
            "Only create SEARCH and REPLACE sections for file that the user has added to the\n"
            "chat!\n"
            "\n"
            "If you want to move code within a file, you need to make two separate edit\n"
            "operations: delete the original code chunk and then insert it in another\n"
            "location.\n"
        ),
        func=None,
        coroutine=execute_search_replace,
        args_schema=SearchReplaceInput,
    )
