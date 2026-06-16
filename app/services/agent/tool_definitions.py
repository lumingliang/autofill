"""
工具定义模块 - 与 1.json 规范完全一致

工具列表：
1. Skill - 执行技能
2. Glob - 文件模式匹配
3. LS - 列出目录
4. Grep - 文本搜索
5. Read - 读取文件
6. RunCommand - 执行命令
7. TodoWrite - 任务管理（支持并发控制）
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict


# ==================== 工具参数 Schema 定义（与 1.json 完全一致） ====================

class SkillInput(BaseModel):
    """Skill 工具输入参数 - 与 1.json 一致"""
    model_config = ConfigDict(extra='forbid')

    name: str = Field(..., description='The skill name (no arguments). E.g., "pdf" or "xlsx"')


class GlobInput(BaseModel):
    """Glob 工具输入参数 - 与 1.json 一致"""
    model_config = ConfigDict(extra='forbid')

    pattern: str = Field(..., description='The glob pattern to match files against.')
    path: Optional[str] = Field(None, description='The directory to search in. If not specified, the current working directory will be used. Omit this field to use the default directory. DO NOT enter "undefined" or "null" - simply omit it for the default behavior. Must be a valid absolute directory path if provided.')


class LSInput(BaseModel):
    """LS 工具输入参数 - 与 1.json 一致"""
    model_config = ConfigDict(extra='forbid')

    path: str = Field(..., description='The absolute path to the directory to list (must be absolute, not relative).')
    ignore: Optional[List[str]] = Field(None, description='List of glob patterns to ignore.')


class GrepInput(BaseModel):
    """Grep 工具输入参数 - 与 1.json 一致

    注意：-A, -B, -C, -i, -n 使用 alias 映射到 1.json 的字段名
    """
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    pattern: str = Field(..., description='The regular expression pattern to search for in file contents')
    path: Optional[str] = Field(None, description='File or directory to search in (rg PATH). Defaults to current working directory.')
    glob: Optional[str] = Field(None, description='Glob pattern to filter files (e.g. "*.js", "**/*.tsx") - maps to rg --glob')
    type: Optional[str] = Field(None, description='File type to search (rg --type). Common types: js, py, rust, go, java, etc. More efficient than include for standard file types.')
    output_mode: Optional[str] = Field("files_with_matches", description='Output mode: "content" shows matching lines (supports -A/-B/-C context, -n line numbers, head_limit), "files_with_matches" shows only file paths (supports head_limit), "count" shows match counts (supports head_limit). Defaults to "files_with_matches".')
    head_limit: Optional[int] = Field(100, description='Limit output to first N lines/entries, equivalent to "| head -N". Works across all output modes: content (limits output lines), files_with_matches (limits file paths), count (limits count entries). Defaults to 100.')
    offset: Optional[int] = Field(0, description='Skip first N lines/entries before applying head_limit, equivalent to "| tail -n +N | head -N". Works across all output modes. Defaults to 0.')
    multiline: Optional[bool] = Field(False, description='Enable multiline mode where . matches newlines and patterns can span lines (rg -U --multiline-dotall). Default: false.')
    # 使用 alias 来支持 -A, -B, -C 等字段名
    A: Optional[int] = Field(None, alias="-A", description='Number of lines to show after each match (rg -A). Requires output_mode: "content", ignored otherwise.')
    B: Optional[int] = Field(None, alias="-B", description='Number of lines to show before each match (rg -B). Requires output_mode: "content", ignored otherwise.')
    C: Optional[int] = Field(None, alias="-C", description='Number of lines to show before and after each match (rg -C). Requires output_mode: "content", ignored otherwise.')
    i: Optional[bool] = Field(False, alias="-i", description='Case insensitive search (rg -i)')
    n: Optional[bool] = Field(False, alias="-n", description='Show line numbers in output (rg -n). Requires output_mode: "content", ignored otherwise.')


class ReadInput(BaseModel):
    """Read 工具输入参数 - 与 1.json 一致"""
    model_config = ConfigDict(extra='forbid')

    file_path: str = Field(..., description='The absolute path to the file to read.')
    limit: int = Field(..., ge=1, le=1000, description='The number of lines to read (must be at least 1, cannot be negative). This parameter is required and controls how many lines to read from the file.')
    offset: Optional[int] = Field(None, ge=1, description='The line number to start reading from (must be at least 1). Only provide if the file is too large to read at once.')


class RunCommandInput(BaseModel):
    """RunCommand 工具输入参数 - 与 1.json 一致"""
    model_config = ConfigDict(extra='forbid')

    command: str = Field(..., description='The terminal command to execute.')
    blocking: bool = Field(..., description='Set to `false` ONLY for web_server or long_running_process command types. Set to `true` for all other cases.')
    requires_approval: bool = Field(..., description='Whether the user must approval the command before it is executed. Set to \'false\' for safe operations like read/write files/directories, create/initialize/build projects, install project dependencies, running development servers.')
    cwd: Optional[str] = Field(None, description='The working directory to run the command in, the value MUST be absolute path, if not provided, it will be the current working directory.')
    command_type: Optional[str] = Field(None, description='Classify the command type BEFORE deciding [blocking]. Available types: [web_server, long_running_process, short_running_process, other].')
    target_terminal: Optional[str] = Field(None, description='The target terminal for command execution. Can be a terminal id (from <available_terminal/> or previous <toolcall_result/>), or \'new\' to create a new terminal. If not specified, the system will automatically reuse an idle AI terminal or create a new one if none is available. For performance, prefer reusing existing idle terminals.')
    wait_ms_before_async: Optional[int] = Field(0, description='This configuration applies only when [blocking] is set to false. It defines the number of milliseconds to pause after initiating the command before letting it proceed in full asynchronous mode. This delay is beneficial for commands that are meant to run asynchronously but might fail almost immediately with an error; the wait allows you to detect and observe any errors that occur during this initial period. If you prefer not to wait, set this value to 0.')


class TodoItem(BaseModel):
    """Todo 任务项定义 - 与 1.json 一致"""
    model_config = ConfigDict(extra='forbid')

    id: str = Field(..., description='Unique identifier for the todo item')
    content: str = Field(..., description='The description/content of the todo item. Make sure the language of todo item content is consistent with the language of <user_input>!')
    status: str = Field(..., description='The current status of the todo item', enum=['pending', 'in_progress', 'completed'])
    priority: str = Field(..., enum=['high', 'medium', 'low'])
    summary: Optional[str] = Field(None, description='Include `summary` only when marking tasks as completed. Describe what was done and the outcomes.')


class TodoWriteInput(BaseModel):
    """TodoWrite 工具输入参数 - 与 1.json 一致

    支持复杂任务管理，包括：
    - 任务列表的创建和更新
    - 任务状态管理
    """
    model_config = ConfigDict(extra='forbid')

    todos: List[TodoItem] = Field(..., description='Array of todo items to write to the workspace', min_items=3, max_items=10)
    merge: bool = Field(..., description='Whether to merge the todos with the existing todos. If true, the todos will be merged into the existing todos based on the id field. You can leave unchanged properties undefined. If false, the new todos will replace the existing todos.')


class SearchReplaceInput(BaseModel):
    """SearchReplace 工具输入参数 - 与 1.json 一致"""
    model_config = ConfigDict(extra='forbid')

    file_path: str = Field(..., description='The file path, you MUST set file path to absolute path.')
    old_str: str = Field(..., description='The SEARCH section, a contiguous chunk of lines to search for in the existing source code.')
    new_str: str = Field(..., description='The REPLACE section, the lines to replace into the source code.')


class WriteInput(BaseModel):
    """Write 工具输入参数 - 与 1.json 一致"""
    model_config = ConfigDict(extra='forbid')

    file_path: str = Field(..., description='The absolute path to the file to write (must be absolute, not relative)')
    content: str = Field(..., description='The content to write to the file')


class DeleteFileInput(BaseModel):
    """DeleteFile 工具输入参数 - 与 1.json 一致"""
    model_config = ConfigDict(extra='forbid')

    file_paths: List[str] = Field(..., description='The list of file paths you want to delete, you MUST set file path to absolute path.')


# ==================== 工具定义列表 ====================

def get_tool_definitions() -> List[Dict[str, Any]]:
    """获取工具定义（与 1.json 完全一致）"""

    # Skill 工具的完整描述，与 1.json 一致
    skill_description = '''Execute a skill within the main conversation
<skills_instructions>
When users ask you to perform tasks, check if any of the available skills below can help complete the task more effectively. Skills provide specialized capabilities and domain knowledge.
How to use skills:
- Invoke skills using this tool with the skill name only (no arguments)
- When you invoke a skill, you will see <command-message>The "{{name}}" skill is loading</command-message>
- The skill's prompt will expand and provide detailed instructions on how to complete the task
- Examples:
  - `command: "autofill-form"` - invoke the autofill-form skill
Important:
- When a skill is relevant, you must invoke this tool IMMEDIATELY as your first action
- NEVER just announce or mention a skill in your text response without actually calling this tool
- This is a BLOCKING REQUIREMENT: invoke the relevant Skill tool BEFORE generating any other response about the task
- Only use skills listed in <available_skills> below
- Do not invoke a skill that is already running
- Do not use this tool for built-in CLI commands (like /help, /clear, etc.)
</skills_instructions>
<available_skills>
<skill>
<name>
autofill-form
</name>
<description>
执行自动填单流程，根据对话内容智能填写表单字段，包括三级事件类型选择和服务记录总结生成。Invoke when user needs to fill a form, process service records, or complete event type classification.
</description>
</skill>
</available_skills>'''

    return [
        {
            "type": "function",
            "function": {
                "name": "Skill",
                "description": skill_description,
                "parameters": SkillInput.schema()
            }
        },
        {
            "type": "function",
            "function": {
                "name": "Glob",
                "description": "Fast file pattern matching tool that works with any codebase size\n\nUsage:\n  - Supports glob patterns like \"/*.js\" or \"src//*.ts\"\n  - Returns matching file paths sorted by modification time\n  - Use this tool when you need to find files by name patterns\n  - When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the `SearchCodebase` tool instead\n  - You can call multiple tools in a single response. It is always better to speculatively perform multiple searches in parallel if they are potentially useful.",
                "parameters": GlobInput.schema()
            }
        },
        {
            "type": "function",
            "function": {
                "name": "LS",
                "description": "Lists files and directories in a given path.\nThe path parameter must be an absolute path, not a relative path.\nYou can optionally provide an array of glob patterns to ignore with the ignore parameter.",
                "parameters": LSInput.schema()
            }
        },
        {
            "type": "function",
            "function": {
                "name": "Grep",
                "description": "A powerful search tool built on ripgrep\n\n  Usage:\n  - NEVER invoke `grep` or `rg` as a Bash command. The Grep tool has been optimized for correct permissions and access.\n  - Supports full regex syntax (e.g., \"log.*Error\", \"function\\s+\\w+\")\n  - Filter files with glob parameter (e.g., \"*.js\", \"**/*.tsx\") or type parameter (e.g., \"js\", \"py\", \"rust\")\n  - Output modes: \"content\" shows matching lines, \"files_with_matches\" shows only file paths (default), \"count\" shows match counts\n  - Pattern syntax: Uses ripgrep (not grep) - literal braces need escaping (use `interface\\{\\}` to find `interface{}` in Go code)\n  - Multiline matching: By default patterns match within single lines only. For cross-line patterns like `struct \\{[\\s\\S]*?field`, use `multiline: true`\n  - Prefer `SearchCodebase` tool when precise code keywords are missing",
                "parameters": GrepInput.schema(by_alias=True)
            }
        },
        {
            "type": "function",
            "function": {
                "name": "Read",
                "description": "Reads a file from the local filesystem. You can access any file directly by using this tool.\nAssume this tool is able to read all files on the machine. If the User provides a path to a file assume that path is valid. It is okay to read a file that does not exist; an error will be returned.\n\nUsage:\n  - The file_path parameter must be an absolute path, not a relative path\n  - You can optionally specify a line offset and limit (especially handy for long files)\n  - Results are returned using cat -n format, with line numbers starting at 1\n  -  When you already know which part of the file you need, only read that part. This can be important for larger files.\n  - You have the capability to call multiple tools in a single response. It is always better to speculatively read multiple files as a batch that are potentially useful.\n  - If you read a file that exists but has empty contents you will receive a system reminder warning in place of file contents.\nImage Support:\n- This tool can also read image files when called with the appropriate path.\n- Supported image formats: PNG, JPG, JPEG, GIF, WEBP.\n- Image files have a size limit of 10MB. The offset and limit parameters are ignored for image files.\n\n\nVideo Support:\n- This tool can also read video files. When a video file is provided, it will be processed and analyzed by a vision model, returning a detailed text description of the video content instead of raw file bytes.\n- Supported video formats: MP4, MPEG, MOV, AVI, FLV, MPG, WEBM, WMV, 3GPP. The offset and limit parameters are ignored for video files.\n- The returned description covers visual content, actions, scene transitions, and any visible text in the video.\n- You MUST always provide the `target` parameter when reading a video file. Use `target` to clearly describe what aspect of the video you want the tool to focus on, such as UI interactions, error messages on screen, the data flow shown in an animation, or the code changes demonstrated in a screen recording.\n- For longer videos, you MUST call this tool multiple times on the same file before making a final judgment. Start from the full timeline and overall workflow, then narrow down to specific time windows, then to local screen regions or components, and finally to the exact visual details that matter for the task.\n- All understanding of video content MUST be grounded in what this tool has actually confirmed from the video. Do NOT guess, imagine, infer, or fill in missing details from prior knowledge or common patterns. If a detail has not been visually confirmed yet, call this tool again with a narrower `target`, or explicitly state that the detail is unknown.\n- **IMPORTANT — Multi-pass requirement for detail-sensitive tasks**: When the task is detail-sensitive — such as debugging a visual issue, reproducing a UI flow, analyzing an error state, replicating a design, recreating an animation, or implementing a demonstrated feature — you MUST analyze the video in multiple passes along both the time axis and the screen-detail axis. First, split the video by timeline to understand the full sequence and identify key stages or suspicious time windows. Then split those specific time windows into full-screen states, major regions, local components, and finally the exact detail level needed, including text, visual states, interactions, and motion changes. Do not stop at a high-level summary when the task depends on precise evidence.\n- **IMPORTANT — Time-aware and screen-aware narrowing**: Video analysis must respect both temporal structure and visual structure. Your follow-up passes should narrow from full video -> key time segment -> smaller time window, and also from full screen -> region -> component -> local detail. If motion or interaction is important, further narrow the analysis to the exact trigger moment, transition process, and final visual state.\n- **Requesting structured output via `target`**: When you need implementation-ready details, you can instruct the vision model through the `target` parameter to return structured descriptions such as HTML/CSS for layout and styling, SVG for icons and vector graphics, CSS @keyframes for motion and transitions, or design token tables for colors, typography, and spacing.\n\nBAD (too vague, missing time scope, screen scope, or motion scope):\n  \"analyze the video\"\n  \"describe what happens\"\n  \"look at the UI\"\n  \"check whether there is a bug\"\n  \"look at the problematic part\"\n\nGOOD (specific, time-split, screen-split, motion-split, produces actionable output):\n  \"First analyze the full timeline of the video and split it into major stages. Identify the exact time window where the abnormal behavior first appears. Then focus only on that time window and describe the full-screen UI state, the major regions on screen, and which local component appears to be involved. Finally, zoom in on that component and explain the trigger action, the state before the interaction, the transition process, any animation or visual change during the interaction, and the final resulting state. Explicitly compare expected behavior vs actual behavior, and mark any unconfirmed details as unknown.\"\n  \"Break this screen recording into timeline segments. For each key segment, describe the full-page layout first, then the relevant region, then the specific component being interacted with. For the critical interaction segment, describe exactly when the interaction starts, what visual changes happen frame-by-frame or step-by-step, whether motion is smooth or abnormal, what text or status changes appear, and what the final rendered result looks like.\"\n  \"Analyze this video for implementation-ready design details in three layers: (1) timeline layer — what the user sees at the start, during each transition, and at the end; (2) screen layer — overall layout, then header / content / footer or other major regions, then the target component; (3) motion layer — trigger condition, animation phases, duration, easing, visual state changes, and final resting appearance. Return only visually confirmed details.\"",
                "parameters": ReadInput.schema()
            }
        },
        {
            "type": "function",
            "function": {
                "name": "RunCommand",
                "description": "Execute a command in a terminal session on behalf of the user.\nEnsure the command is compatible with the current operating system (macos).\n\n\n\nIMPORTANT: This tool is for terminal operations like git, npm, docker, build scripts, etc. DO NOT use it for file operations (reading, writing, editing, searching, finding files) — use the specialized tools for these instead.\n\nBefore executing the command, follow these steps:\n1. Directory Verification:\n  - If the command creates new directories or files, first verify the parent directory exists.\n  - Use the `cwd` parameter to specify the working directory rather than prepending `cd`.\n\n2. Command Execution:\n  - Always quote file paths that contain spaces with double quotes (e.g., cd \"path with spaces/file.txt\").\n  - You MUST avoid generating interactive commands unless the command only supports interactive input. For example, run `npm create vite@latest . -- --template react` instead of `npm create vite@latest .`.\n\nUsage notes:\n  - Terminals are stateful across sequential calls. Current working directory, environment variables, and state persist between calls within the same terminal.\n  - For performance, prefer reusing existing idle terminals. The system will automatically find and reuse an idle AI terminal when `target_terminal` is not specified.\n  - Commands will be run with PAGER=cat. You may want to limit the length of output for commands that usually rely on paging and may contain very long output (e.g. for git log, use git log -n <N> ; for man ls, man ls | head -n <N>).\n  - VERY IMPORTANT: You MUST avoid using search commands like `find` and `grep`. Use Grep, Glob,SearchCodebase tools instead. You MUST avoid read commands like `cat`, `head`, `tail`. Use the Read tool instead. Avoid editing files with `sed` and `awk`. Use the Edit tool instead.\n  - If you need to observe real-time output from a non-blocking command (blocking: false), use the CheckCommandStatus tool with the command's ID. Do not re-run the command — CheckCommandStatus lets you retrieve the latest output on demand.\n  - To stop a running command, use the StopCommand tool with the command's ID. Do not use `kill`, `pkill`, or other shell commands to terminate processes — StopCommand is the dedicated way.\n  - When issuing multiple commands:\n    - If the commands are independent and can run in parallel, make multiple RunCommand tool calls in a single message. For example, if you need to run \"git status\" and \"git diff\", send a single message with two RunCommand tool calls in parallel.\n    - If the commands depend on each other and must run sequentially, use a single RunCommand call with '&&' to chain them together (e.g., `git add . && git commit -m \"message\" && git push`). For instance, if one operation must complete before another starts (like mkdir before cp,Write before RunCommand for git operations, or git add before git commit), run these operations sequentially instead.\n    - Use ';' only when you need to run commands sequentially but don't care if earlier commands fail\n    - DO NOT use newlines to separate commands (newlines are ok in quoted strings)\n\n### Git Safety Protocol:\n  - NEVER update the git config\n  - NEVER run destructive git commands (push --force, reset --hard, checkout ., restore ., clean -f, branch -D) unless the user explicitly requests these actions. Taking unauthorized destructive actions is unhelpful and can result in lost work, so it's best to ONLY run these commands when given direct instructions \n  - NEVER run force push to main/master, warn the user if they request it\n  - When staging files, prefer adding specific files by name rather than using \"git add -A\" or \"git add .\", which can accidentally include sensitive files (.env, credentials) or large binaries\n  - NEVER commit changes unless the user explicitly asks you to. It is VERY IMPORTANT to only commit when explicitly asked, otherwise the user will feel that you are being too proactive\n\n### Committing changes with git\n\nOnly create commits when requested by the user. If unclear, ask first. When the user asks you to create a new git commit, follow these steps carefully:\n\n1. Run the following commands in parallel, each using the RunCommand tool:\n  - Run a git status command to see all untracked files. IMPORTANT: Never use the -uall flag as it can cause memory issues on large repos.\n  - Run a git diff command to see both staged and unstaged changes that will be committed.\n  - Run a git log command to see recent commit messages, so that you can follow this repository's commit message style.\n2. Analyze all staged changes (both previously staged and newly added) and draft a commit message:\n  - Summarize the nature of the changes (eg. new feature, enhancement to an existing feature, bug fix, refactoring, test, docs, etc.). Ensure the message accurately reflects the changes and their purpose (i.e. \"add\" means a wholly new feature, \"update\" means an enhancement to an existing feature, \"fix\" means a bug fix, etc.).\n  - Do not commit files that likely contain secrets (.env, credentials.json, etc). Warn the user if they specifically request to commit those files\n  - Draft a concise (1-2 sentences) commit message that focuses on the \"why\" rather than the \"what\"\n  - Ensure it accurately reflects the changes and their purpose\n3. Run the following commands in parallel:\n  - Add relevant untracked files to the staging area.\n  - Run git status after the commit completes to verify success.\n  Note: git status depends on the commit completing, so run it sequentially after the commit.\n\nImportant notes:\n- NEVER run additional commands to read or explore code, besides git  commands\n- NEVER use the TodoWrite or Task tools\n- DO NOT push to the remote repository unless the user explicitly asks you to do so\n- IMPORTANT: Never use git commands with the -i flag (like git rebase -i or git add -i) since they require interactive input which is not supported.\n- IMPORTANT: Do not use --no-edit with git rebase commands, as the --no-edit flag is not a valid option for git rebase.\n- If there are no changes to commit (i.e., no untracked files and no modifications), do not create an empty commit\n- In order to ensure good formatting, ALWAYS pass the commit message via a HEREDOC, a la this example:\n<example>\ngit commit -m \"$(cat <<'EOF'\n  Commit message here.\n\n  EOF\n  )\"\n</example>\n\n### Pushing changes to remote\n\nWhen the user asks you to push changes, follow these steps:\n\n1. Run the following commands in parallel to understand the current state:\n  - `git status` to see all untracked and modified files (never use the -uall flag)\n  - `git log --oneline -5` to see recent commits\n  - `git branch -vv` to check if the current branch tracks a remote and is up to date\n\n2. Based on the results:\n  - If there are uncommitted changes, ask the user whether to commit first (do NOT commit automatically unless explicitly requested)\n  - If the branch has no upstream, use `git push -u origin <branch>` to set tracking\n  - If the branch already tracks a remote, use `git push`\n\nImportant:\n- NEVER use `git push --force` or `git push --force-with-lease` unless the user explicitly requests it\n- NEVER push to main/master directly — warn the user if they request it\n- If the push fails due to remote changes, suggest `git pull --rebase` first rather than force pushing\n- DO NOT use the TodoWrite or Task tools\n- Return merge request/pr/pull request link if available",
                "parameters": RunCommandInput.schema()
            }
        },
        {
            "type": "function",
            "function": {
                "name": "TodoWrite",
                "description": "Use this tool to create and manage a structured task list for your current coding session. This helps track progress, organize complex tasks, and demonstrate thoroughness to the user.\nNote: Other than when first creating todos, don't tell the user you're updating todos, just do it.\n### When to Use\nUse for complex tasks with 3+ distinct steps, or when the user explicitly requests a todo list.\nSkip for simple tasks (< 3 steps) or purely conversational requests.\n### merge Parameter\n- merge=false: Replace the entire todo list. Use when creating a fresh plan.\n- merge=true: Merge into the existing list by id. Only id and changed fields are required for updates; all fields required for new items.\n### Task States & Display Order\n- pending / in_progress / completed\n- Only ONE task may be in_progress at a time.\n- Mark tasks complete IMMEDIATELY after finishing, before starting the next.\n- Todos are displayed sorted by: status (in_progress > pending > completed), then priority (high > medium > low), then creation time. Assign priority based on actual importance to the user.\n### Summary Field\nInclude `summary` only when marking tasks as completed. Describe what was done and the outcomes.\n### Parallel Tool Calls\n- Prefer creating the first todo as in_progress.\n- Start working on todos by using tool calls in the same tool call batch as the todo write.\n- Batch todo updates with other tool calls for better latency and lower costs for the user.\n### IMPORTANT\n- When the user sends a new task that supersedes the current todo_list, use merge=false to replace the todo list instead of merging.\n- Do not end your turn before all todos are completed.\n- All required fields (content, status, id, priority) must be provided when creating new items. When updating existing items via merge=true, content and priority can be omitted to preserve their current values.  ",
                "parameters": TodoWriteInput.schema()
            }
        },
        {
            "type": "function",
            "function": {
                "name": "Write",
                "description": "Writes a file to the local filesystem.\n\nUsage:\n- This tool will overwrite the existing file if there is one at the provided path.\n- If this is an existing file, you MUST use the Read tool first to read the file's contents. This tool will fail if you did not read the file first.\n- ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.\n- NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.\n- Only use emojis if the user explicitly requests it. Avoid writing emojis to files unless asked.",
                "parameters": WriteInput.schema()
            }
        },
    ]
