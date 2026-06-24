"""
CheckCommandStatus 工具 - 检查异步命令状态
"""
import asyncio
from typing import Optional

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from app.services.agent.command_manager import command_manager
from app.services.agent.tool_executor import format_tool_result


class CheckCommandStatusInput(BaseModel):
    command_id: Optional[str] = Field(default=None, description="ID of the command to get status for.")
    filter: Optional[str] = Field(
        default=None,
        description="Optional regular expression to filter the output lines. Only lines matching this regex will be included in the result. Any lines that do not match will no longer be available to read.\n",
    )
    output_priority: str = Field(
        default="bottom",
        description="Priority for displaying command output. Must be one of: 'top' (show oldest lines), 'bottom' (show newest lines), or 'split' (prioritize oldest and newest lines, excluding middle).\n",
    )
    skip_character_count: int = Field(
        default=0,
        ge=0,
        description="Number of characters to skip from the output_priority position.",
    )
    wait_ms_before_check: int = Field(
        default=0,
        ge=0,
        description="If you expect the command to take longer to complete, you can specify a waiting period in milliseconds before checking its status.\nIf you prefer not to wait, set this value to 0.\n",
    )
    output_character_count: int = Field(
        default=2000,
        ge=0,
        description="Number of characters to view. Make this as small as possible to avoid excessive memory usage.",
    )


async def execute_check_command_status(
    command_id: str,
    filter: Optional[str] = None,
    output_priority: str = "bottom",
    skip_character_count: int = 0,
    wait_ms_before_check: int = 0,
    output_character_count: int = 2000,
) -> str:
    """检查命令状态"""
    if wait_ms_before_check and wait_ms_before_check > 0:
        await asyncio.sleep(min(wait_ms_before_check / 1000.0, 5.0))

    cmd = command_manager.get_command(command_id)
    if not cmd:
        return format_tool_result("error", {"error": f"Command not found: {command_id}"})

    process = cmd.get("process")
    # 如果进程还在运行，尝试快速 poll 一下最新状态
    if process is not None and process.returncode is None:
        try:
            process.returncode = process._transport.get_returncode() if hasattr(process, "_transport") else None
        except Exception:
            pass

    output_info = command_manager.get_output_slice(
        command_id,
        output_character_count=output_character_count,
        output_priority=output_priority,
        skip_character_count=skip_character_count,
        filter_regex=filter,
    )

    return format_tool_result("done", {
        "command_id": command_id,
        "status": cmd.get("status"),
        "exit_code": cmd.get("exit_code"),
        "pid": cmd.get("pid"),
        "output": output_info.get("text"),
        "error": cmd.get("error", "") if not output_info.get("text") else None,
        "total_characters": output_info.get("total_characters"),
        "has_more": output_info.get("has_more"),
    })


def get_check_command_status_tool() -> BaseTool:
    return StructuredTool.from_function(
        name="CheckCommandStatus",
        description=(
            "You can use this tool to get the status of a previously executed command by its Command ID ( non-blocking command ).\n"
            "Returns the current status (running, done), exit code (if done), output lines as specified by output priority, and any error if present.\n"
            "If the user asks about runtime errors, compilation errors, terminal errors, etc., you can also use the provided tool to obtain the current terminal command without setting the Command ID.\n"
            "If there is a non-blocking command is initializing in previous toolcall, you should use this tool to get the current status of that command.\n"
            "If there is no **Command ID** information in previous toolcall, you MUST not use this tool.\n"
            "If the output is long, this tool will only get part of the output and the rest will be replaced with (some characters truncated). You can call this tool multiple times with the same command_id, and set skip_character_count to get more output contents.\n"
            "You MUST not call this tool with the same command_id more than 3 times, as it consumes excessive resources and is inefficient.\n"
            "\n"
            "Example:\n"
            "```\n"
            "$ ls -a\n"
            ".bashrc\n"
            ".zshrc\n"
            "Workspace\n"
            "```\n"
            "* If you set 'output_priority' to 'bottom' and 'output_character_count' to 10, you will get the output \"c\\nWorkspace\".\n"
            "* If you set 'output_priority' to 'bottom' and 'output_character_count' to 10 and 'skip_character_count' to 10, you will get the output \"shrc\\n.zshr\".\n"
        ),
        func=None,
        coroutine=execute_check_command_status,
        args_schema=CheckCommandStatusInput,
    )
