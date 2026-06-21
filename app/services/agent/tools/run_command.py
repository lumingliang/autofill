"""
RunCommand 工具 - 执行命令
"""
import asyncio
import os
import shlex
import subprocess
from datetime import datetime
from typing import Optional

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from app.services.agent.command_manager import command_manager
from app.services.agent.tool_executor import format_tool_result


# 危险命令黑名单（简单校验）
# 注意：条目应足够具体，避免误伤合法参数（如 --format json）
_DANGEROUS_COMMANDS = [
    "rm -rf /", "rm -rf /*", ":(){ :|:& };:", "> /dev/sda", "dd if=/dev/zero",
    "mkfs.", "fdisk", "shutdown", "reboot", "halt", "poweroff",
]


class RunCommandInput(BaseModel):
    command: str = Field(description="The terminal command to execute.")
    cwd: Optional[str] = Field(default=None, description=(
        "The working directory to run the command in, the value MUST be absolute path, if\n"
        "not provided, it will be the current working directory."
    ))
    blocking: bool = Field(description=(
        "Set to `false` ONLY for web_server or long_running_process command types. Set to\n"
        "`true` for all other cases.\n"
    ))
    command_type: Optional[str] = Field(default=None, description=(
        "Classify the command type BEFORE deciding [blocking]. Available types:\n"
        "[web_server, long_running_process, short_running_process, other].\n"
    ))
    target_terminal: Optional[str] = Field(default=None, description=(
        "The target terminal for command execution. Can be a terminal id (from\n"
        "<available_terminal/> or previous <toolcall_result/>), or 'new' to create a new\n"
        "terminal. If not specified, the system will automatically reuse an idle AI\n"
        "terminal or create a new one if none is available. For performance, prefer\n"
        "reusing existing idle terminals."
    ))
    requires_approval: bool = Field(description=(
        "Whether the user must approval the command before it is executed. Set to 'false'\n"
        "for safe operations like read/write files/directories, create/initialize/build\n"
        "projects, install project dependencies, running development servers.\n"
    ))
    wait_ms_before_async: Optional[int] = Field(default=0, ge=0, description=(
        "This configuration applies only when [blocking] is set to false.\n"
        "It defines the number of milliseconds to pause after initiating the command\n"
        "before letting it proceed in full asynchronous mode.\n"
        "This delay is beneficial for commands that are meant to run asynchronously but\n"
        "might fail almost immediately with an error; the wait allows you to detect and\n"
        "observe any errors that occur during this initial period.\n"
        "If you prefer not to wait, set this value to 0.\n"
    ))


def _validate_command(command: str) -> tuple[bool, Optional[str]]:
    """校验命令是否安全（当前阶段暂时放行，优先保证命令可执行）"""
    # stripped = command.strip().lower()
    # for dangerous in _DANGEROUS_COMMANDS:
    #     if dangerous in stripped:
    #         return False, f"Dangerous command detected: {dangerous}"
    return True, None


async def execute_run_command(
    command: str,
    cwd: Optional[str] = None,
    blocking: bool = True,
    command_type: Optional[str] = None,
    target_terminal: Optional[str] = None,
    requires_approval: bool = False,
    wait_ms_before_async: int = 0,
) -> str:
    """执行 RunCommand 工具 - 与 1.json 一致"""
    work_dir = cwd or os.getcwd()

    safe, reason = _validate_command(command)
    if not safe:
        return format_tool_result("error", {"error": reason})

    # 创建命令记录
    command_id = command_manager.create_command(
        command=command,
        cwd=work_dir,
        blocking=blocking,
        wait_ms=wait_ms_before_async
    )

    if not blocking and wait_ms_before_async > 0:
        await asyncio.sleep(wait_ms_before_async / 1000)

    try:
        command_manager.update_command(
            command_id,
            status="running",
            started_at=datetime.now().isoformat()
        )

        # 使用 shell=False 安全执行，通过 shlex.split 解析命令
        cmd_args = shlex.split(command)
        result = subprocess.run(
            cmd_args,
            shell=False,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=300 if blocking else 1
        )

        command_manager.update_command(
            command_id,
            status="completed",
            exit_code=result.returncode,
            output=result.stdout,
            error=result.stderr,
            completed_at=datetime.now().isoformat()
        )

        return format_tool_result("done", {
            "command_id": command_id,
            "status": "completed",
            "exit_code": result.returncode,
            "output": result.stdout[:5000],
            "error": result.stderr[:2000] if result.stderr else None,
        })

    except subprocess.TimeoutExpired:
        command_manager.update_command(
            command_id,
            status="running",
            output="Command is still running..."
        )
        return format_tool_result("running", {
            "command_id": command_id,
            "status": "running",
            "message": "Command is running asynchronously"
        })

    except Exception as e:
        command_manager.update_command(
            command_id,
            status="error",
            error=str(e)
        )
        return format_tool_result("error", {
            "command_id": command_id,
            "status": "error",
            "error": str(e)
        })


def get_run_command_tool() -> BaseTool:
    return StructuredTool.from_function(
        name="RunCommand",
        description=(
            "Execute a command in a terminal session on behalf of the user.\n"
            "Ensure the command is compatible with the current operating system (macos).\n"
            "\n"
            "\n"
            "\n"
            "IMPORTANT: This tool is for terminal operations like git, npm, docker, build scripts, etc. DO NOT use it for file operations (reading, writing, editing, searching, finding files) — use the specialized tools for these instead.\n"
            "\n"
            "Before executing the command, follow these steps:\n"
            "1. Directory Verification:\n"
            "  - If the command creates new directories or files, first verify the parent directory exists.\n"
            "  - Use the `cwd` parameter to specify the working directory rather than prepending `cd`.\n"
            "\n"
            "2. Command Execution:\n"
            "  - Always quote file paths that contain spaces with double quotes (e.g., cd \"path with spaces/file.txt\").\n"
            "  - You MUST avoid generating interactive commands unless the command only supports interactive input. For example, run `npm create vite@latest . -- --template react` instead of `npm create vite@latest .`.\n"
            "\n"
            "Usage notes:\n"
            "  - Terminals are stateful across sequential calls. Current working directory, environment variables, and state persist between calls within the same terminal.\n"
            "  - For performance, prefer reusing existing idle terminals. The system will automatically find and reuse an idle AI terminal when `target_terminal` is not specified.\n"
            "  - Commands will be run with PAGER=cat. You may want to limit the length of output for commands that usually rely on paging and may contain very long output (e.g. for git log, use git log -n <N> ; for man ls, man ls | head -n <N>).\n"
            "  - VERY IMPORTANT: You MUST avoid using search commands like `find` and `grep`. Use Grep, Glob,SearchCodebase tools instead. You MUST avoid read commands like `cat`, `head`, `tail`. Use the Read tool instead. Avoid editing files with `sed` and `awk`. Use the Edit tool instead.\n"
            "  - If you need to observe real-time output from a non-blocking command (blocking: false), use the CheckCommandStatus tool with the command's ID. Do not re-run the command — CheckCommandStatus lets you retrieve the latest output on demand.\n"
            "  - To stop a running command, use the StopCommand tool with the command's ID. Do not use `kill`, `pkill`, or other shell commands to terminate processes — StopCommand is the dedicated way.\n"
            "  - When issuing multiple commands:\n"
            "    - If the commands are independent and can run in parallel, make multiple RunCommand tool calls in a single message. For example, if you need to run \"git status\" and \"git diff\", send a single message with two RunCommand tool calls in parallel.\n"
            "    - If the commands depend on each other and must run sequentially, use a single RunCommand call with '&&' to chain them together (e.g., `git add . && git commit -m \"message\" && git push`). For instance, if one operation must complete before another starts (like mkdir before cp,Write before RunCommand for git operations, or git add before git commit), run these operations sequentially instead.\n"
            "    - Use ';' only when you need to run commands sequentially but don't care if earlier commands fail\n"
            "    - DO NOT use newlines to separate commands (newlines are ok in quoted strings)\n"
            "\n"
            "### Git Safety Protocol:\n"
            "  - NEVER update the git config\n"
            "  - NEVER run destructive git commands (push --force, reset --hard, checkout ., restore ., clean -f, branch -D) unless the user explicitly requests these actions. Taking unauthorized destructive actions is unhelpful and can result in lost work, so it's best to ONLY run these commands when given direct instructions \n"
            "  - NEVER run force push to main/master, warn the user if they request it\n"
            "  - When staging files, prefer adding specific files by name rather than using \"git add -A\" or \"git add .\", which can accidentally include sensitive files (.env, credentials) or large binaries\n"
            "  - NEVER commit changes unless the user explicitly asks you to. It is VERY IMPORTANT to only commit when explicitly asked, otherwise the user will feel that you are being too proactive\n"
            "\n"
            "### Committing changes with git\n"
            "\n"
            "Only create commits when requested by the user. If unclear, ask first. When the user asks you to create a new git commit, follow these steps carefully:\n"
            "\n"
            "You can call multiple commands in parallel, each using the RunCommand tool:\n"
            "  - Run a git status command to see all untracked files. IMPORTANT: Never use the -uall flag as it can cause memory issues on large repos.\n"
            "  - Run a git diff command to see both staged and unstaged changes that will be committed.\n"
            "  - Run a git log command to see recent commit messages, so that you can follow this repository's commit message style.\n"
            "2. Analyze all staged changes (both previously staged and newly added) and draft a commit message:\n"
            "  - Summarize the nature of the changes (eg. new feature, enhancement to an existing feature, bug fix, refactoring, test, docs, etc.). Ensure the message accurately reflects the changes and their purpose (i.e. \"add\" means a wholly new feature, \"update\" means an enhancement to an existing feature, \"fix\" means a bug fix, etc.)\n"
            "  - Do not commit files that likely contain secrets (.env, credentials.json, etc). Warn the user if they specifically request to commit those files\n"
            "  - Draft a concise (1-2 sentences) commit message that focuses on the \"why\" rather than the \"what\"\n"
            "  - Ensure it accurately reflects the changes and their purpose\n"
            "3. Run the following commands in parallel:\n"
            "  - Add relevant untracked files to the staging area.\n"
            "  - Run git status after the commit completes to verify success.\n"
            "  Note: git status depends on the commit completing, so run it sequentially after the commit.\n"
            "\n"
            "Important notes:\n"
            "- NEVER run additional commands to read or explore code, besides git  commands\n"
            "- NEVER use the TodoWrite or Task tools\n"
            "- DO NOT push to the remote repository unless the user explicitly asks you to do so\n"
            "- IMPORTANT: Never use git commands with the -i flag (like git rebase -i or git add -i) since they require interactive input which is not supported.\n"
            "- IMPORTANT: Do not use --no-edit with git rebase commands, as the --no-edit flag is not a valid option for git rebase.\n"
            "- If there are no changes to commit (i.e., no untracked files and no modifications), do not create an empty commit\n"
            "- In order to ensure good formatting, ALWAYS pass the commit message via a HEREDOC, a la this example:\n"
            "<example>\n"
            "git commit -m \"$(cat <<'EOF'\n"
            "  Commit message here.\n"
            "\n"
            "  EOF\n"
            "  )\"\n"
            "</example>\n"
            "\n"
            "### Pushing changes to remote\n"
            "\n"
            "When the user asks you to push changes, follow these steps:\n"
            "\n"
            "1. Run the following commands in parallel to understand the current state:\n"
            "  - `git status` to see all untracked and modified files (never use the -uall flag)\n"
            "  - `git log --oneline -5` to see recent commits\n"
            "  - `git branch -vv` to check if the current branch tracks a remote and is up to date\n"
            "\n"
            "2. Based on the results:\n"
            "  - If there are uncommitted changes, ask the user whether to commit first (do NOT commit automatically unless explicitly requested)\n"
            "  - If the branch has no upstream, use `git push -u origin <branch>` to set tracking\n"
            "  - If the branch already tracks a remote, use `git push`\n"
            "\n"
            "Important:\n"
            "- NEVER use `git push --force` or `git push --force-with-lease` unless the user explicitly requests it\n"
            "- NEVER push to main/master directly — warn the user if they request it\n"
            "- If the push fails due to remote changes, suggest `git pull --rebase` first rather than force pushing\n"
            "- DO NOT use the TodoWrite or Task tools\n"
            "- Return merge request/pr/pull request link if available"
        ),
        func=None,
        coroutine=execute_run_command,
        args_schema=RunCommandInput,
    )
