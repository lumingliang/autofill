"""
Grep 工具 - 文本搜索
"""
import os
import subprocess
from typing import Literal, Optional

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field, model_validator

from app.services.agent.tool_executor import format_tool_result


class GrepInput(BaseModel):
    pattern: str = Field(description="The regular expression pattern to search for in file contents")
    path: Optional[str] = Field(default=None, description="File or directory to search in (rg PATH). Defaults to current working directory.")
    glob: Optional[str] = Field(default=None, description='Glob pattern to filter files (e.g. "*.js", "*.{ts,tsx}") - maps to rg --glob')
    type: Optional[str] = Field(default=None, description="File type to search (rg --type). Common types: js, py, rust, go, java, etc. More efficient than include for standard file types.")
    output_mode: Optional[Literal["content", "files_with_matches", "count"]] = Field(default="files_with_matches", description='Output mode: "content" shows matching lines (supports -A/-B/-C context, -n line numbers, head_limit), "files_with_matches" shows file paths (supports head_limit), "count" shows match counts (supports head_limit). Defaults to "files_with_matches".')
    head_limit: Optional[int] = Field(default=100, description='Limit output to first N lines/entries, equivalent to "| head -N". Works across all output modes: content (limits output lines), files_with_matches (limits file paths), count (limits count entries). Defaults to 100.')
    offset: Optional[int] = Field(default=0, description='Skip first N lines/entries before applying head_limit, equivalent to "| tail -n +N | head -N". Works across all output modes. Defaults to 0.')
    multiline: Optional[bool] = Field(default=False, description="Enable multiline mode where . matches newlines and patterns can span lines (rg -U --multiline-dotall). Default: false.")
    A: Optional[int] = Field(default=None, description='Number of lines to show after each match (rg -A). Requires output_mode: "content", ignored otherwise.')
    B: Optional[int] = Field(default=None, description='Number of lines to show before each match (rg -B). Requires output_mode: "content", ignored otherwise.')
    C: Optional[int] = Field(default=None, description='Number of lines to show before and after each match (rg -C). Requires output_mode: "content", ignored otherwise.')
    i: Optional[bool] = Field(default=False, description="Case insensitive search (rg -i)")
    n: Optional[bool] = Field(default=False, description='Show line numbers in output (rg -n). Requires output_mode: "content", ignored otherwise.')

    @model_validator(mode="before")
    @classmethod
    def _accept_cli_aliases(cls, data):
        """允许 LLM 使用与原始 1.json 一致的 -A/-B/-C/-i/-n 参数名。"""
        if not isinstance(data, dict):
            return data
        rename = {"-A": "A", "-B": "B", "-C": "C", "-i": "i", "-n": "n"}
        for old, new in rename.items():
            if old in data and new not in data:
                data[new] = data.pop(old)
        return data

    @classmethod
    def model_json_schema(cls, *args, **kwargs):
        """生成与 1.json 一致的参数名（-A/-B/-C/-i/-n）。"""
        schema = super().model_json_schema(*args, **kwargs)
        rename = {"A": "-A", "B": "-B", "C": "-C", "i": "-i", "n": "-n"}
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for old, new in rename.items():
            if old in properties:
                properties[new] = properties.pop(old)
            if old in required:
                required[required.index(old)] = new
        return schema


async def execute_grep(
    pattern: str,
    path: Optional[str] = None,
    glob: Optional[str] = None,
    type: Optional[str] = None,
    output_mode: str = "files_with_matches",
    head_limit: int = 100,
    offset: int = 0,
    multiline: bool = False,
    A: Optional[int] = None,
    B: Optional[int] = None,
    C: Optional[int] = None,
    i: bool = False,
    n: bool = False,
) -> str:
    """执行 Grep 工具 - 与 1.json 一致"""
    search_path = path or os.getcwd()

    # 构建 ripgrep 命令
    cmd = ["rg", pattern]

    if output_mode == "files_with_matches":
        cmd.append("-l")
    elif output_mode == "count":
        cmd.append("-c")
    elif output_mode == "content":
        if n:
            cmd.append("-n")
        if A is not None:
            cmd.extend(["-A", str(A)])
        if B is not None:
            cmd.extend(["-B", str(B)])
        if C is not None:
            cmd.extend(["-C", str(C)])

    if i:
        cmd.append("-i")

    if multiline:
        cmd.append("-U")

    if glob:
        cmd.extend(["-g", glob])

    if type:
        cmd.extend(["-t", type])

    if head_limit:
        cmd.extend(["-m", str(head_limit)])

    cmd.append(search_path)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return format_tool_result("done", {
            "output": result.stdout,
            "error": result.stderr if result.stderr else None,
            "exit_code": result.returncode
        })
    except Exception as e:
        return format_tool_result("error", {"error": str(e)})


def get_grep_tool() -> BaseTool:
    return StructuredTool.from_function(
        name="Grep",
        description='A powerful search tool built on ripgrep\n\n  Usage:\n  - NEVER invoke `grep` or `rg` as a Bash command. The Grep tool has been optimized for correct permissions and access.\n  - Supports full regex syntax (e.g., "log.*Error", "function\\s+\\w+")\n  - Filter files with glob parameter (e.g., "*.js", "**/*.tsx") or type parameter (e.g., "js", "py", "rust")\n  - Output modes: "content" shows matching lines, "files_with_matches" shows only file paths (default), "count" shows match counts\n  - Pattern syntax: Uses ripgrep (not grep) - literal braces need escaping (use `interface\\{\\}` to find `interface{}` in Go code)\n  - Multiline matching: By default patterns match within single lines only. For cross-line patterns like `struct \\{[\\s\\S]*?field`, use `multiline: true`\n  - Prefer `SearchCodebase` tool when precise code keywords are missing\n',
        func=None,
        coroutine=execute_grep,
        args_schema=GrepInput,
    )
