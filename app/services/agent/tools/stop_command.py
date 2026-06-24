"""
StopCommand 工具 - 停止正在运行的命令
"""
from typing import Optional

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from app.services.agent.command_manager import command_manager
from app.services.agent.tool_executor import format_tool_result


class StopCommandInput(BaseModel):
    command_id: str = Field(
        description="The command id of the running command that you need to terminate. you MUST use correct command id from previously executed command info."
    )


async def execute_stop_command(command_id: str) -> str:
    """停止命令"""
    cmd = command_manager.get_command(command_id)
    if not cmd:
        return format_tool_result("error", {"error": f"Command not found: {command_id}"})

    if cmd.get("status") not in ("created", "running"):
        return format_tool_result("done", {
            "command_id": command_id,
            "status": cmd.get("status"),
            "message": "Command is not running",
        })

    ok = await command_manager.stop_command(command_id)
    cmd = command_manager.get_command(command_id)
    return format_tool_result("done" if ok else "error", {
        "command_id": command_id,
        "status": cmd.get("status") if cmd else "unknown",
        "exit_code": cmd.get("exit_code") if cmd else None,
        "stopped": ok,
    })


def get_stop_command_tool() -> BaseTool:
    return StructuredTool.from_function(
        name="StopCommand",
        description=(
            "This tool allows you to terminate a currently running command( the command MUST be previously executed command. ). You should use this tool when:\n"
            "- You need to restart a command after updating the code;\n"
            "- The user requests to stop the running command;\n"
        ),
        func=None,
        coroutine=execute_stop_command,
        args_schema=StopCommandInput,
    )
