"""
SearchReplace 工具 - 编辑文件
"""
from typing import Optional

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from app.services.agent.tool_executor import format_tool_result


class SearchReplaceInput(BaseModel):
    file_path: str = Field(description="The file path, you MUST set file path to absolute path.")
    old_str: str = Field(description="The SEARCH section, a contiguous chunk of lines to search for in the existing\nsource code.")
    new_str: str = Field(description="The REPLACE section, the lines to replace into the source code.")


async def execute_search_replace(file_path: str, old_str: str, new_str: str) -> str:
    """执行 SearchReplace 工具 - 与 1.json 一致"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if old_str not in content:
            return format_tool_result("error", {
                "error": "old_str not found in file",
                "file_path": file_path
            })

        new_content = content.replace(old_str, new_str, 1)

        if new_content == content:
            return format_tool_result("error", {
                "error": "REPLACE section must be different from SEARCH section",
                "file_path": file_path
            })

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return format_tool_result("done", {
            "file_path": file_path,
            "status": "updated"
        })
    except Exception as e:
        return format_tool_result("error", {"error": str(e)})


def get_search_replace_tool() -> BaseTool:
    return StructuredTool.from_function(
        name="SearchReplace",
        description="You can use this tool to edit file. You should specify the following arguments\nbefore the others: `file_path`\n\nWhen you choose to use this tool to edit a existing file, you MUST follow the\n*SEARCH/REPLACE* Rules to set the `old_str` and `new_str` parameters:\n\n1. The `old_str` is the SEARCH section that should be a contiguous chunk of\nlines to search for in the existing source code.\n2. The `new_str` is the REPLACE section that should be lines to replace into the\nsource code.\n3. The REPLACE section MUST be different from the SEARCH section.\n\nThis tool will *only* replace the first match occurrence of the SEARCH section.\nInclude enough lines in the SEARCH section to uniquely match the set of lines\nthat need to change.\n\nKeep your SEARCH and REPLACE sections concise.\nInclude just the changing lines, and a few surrounding lines if needed for\nuniqueness.\nDo not include long runs of unchanging lines in your SEARCH and REPLACE\nsections.\n\nOnly create SEARCH and REPLACE sections for file that the user has added to the\nchat!\n\nIf you want to move code within a file, you need to make two separate edit\noperations: delete the original code chunk and then insert it in another\nlocation.\n",
        func=None,
        coroutine=execute_search_replace,
        args_schema=SearchReplaceInput,
    )
