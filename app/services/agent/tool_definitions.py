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
8. SearchReplace - 编辑文件
9. Write - 写入文件
10. DeleteFile - 删除文件
11. AskUserQuestion - 询问用户问题
"""
import os
import re
from typing import Any, Dict, List


# ==================== Skill XML 加载 ====================

def _load_skills_xml(skill_dir: str = "/Users/lu/code/code/py/autofill/skill") -> str:
    """从 skill 目录加载本地技能定义，生成 <available_skills> XML 片段"""
    if not os.path.isdir(skill_dir):
        return ""

    skills_xml = []
    for entry in sorted(os.listdir(skill_dir)):
        entry_path = os.path.join(skill_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        skill_md = os.path.join(entry_path, "SKILL.md")
        if not os.path.isfile(skill_md):
            continue

        with open(skill_md, "r", encoding="utf-8") as f:
            content = f.read()

        fm_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not fm_match:
            continue

        name = None
        description = None
        for line in fm_match.group(1).split('\n'):
            line = line.strip()
            if line.startswith('name:'):
                name = line.split(':', 1)[1].strip().strip('"').strip("'")
            elif line.startswith('description:'):
                description = line.split(':', 1)[1].strip().strip('"').strip("'")

        if name and description:
            skills_xml.append(f"""<skill>
<name>
{name}
</name>
<description>
{description}
</description>
</skill>""")

    return "\n".join(skills_xml)


def _skill_description() -> str:
    """生成 Skill 工具的完整 description（与 1.json 一致）"""
    available_skills_xml = _load_skills_xml()
    return f"""Execute a skill within the main conversation
<skills_instructions>
When users ask you to perform tasks, check if any of the available skills below can help complete the task more effectively. Skills provide specialized capabilities and domain knowledge.
How to use skills:
- Invoke skills using this tool with the skill name only (no arguments)
- When you invoke a skill, you will see <command-message>The "{{name}}" skill is loading</command-message>
- The skill's prompt will expand and provide detailed instructions on how to complete the task
- Examples:
  - `command: "pdf"` - invoke the pdf skill
  - `command: "xlsx"` - invoke the xlsx skill
  - `command: "ms-office-suite:pdf"` - invoke using fully qualified name
Important:
- When a skill is relevant, you must invoke this tool IMMEDIATELY as your first action
- NEVER just announce or mention a skill in your text response without actually calling this tool
- This is a BLOCKING REQUIREMENT: invoke the relevant Skill tool BEFORE generating any other response about the task
- Only use skills listed in <available_skills> below
- Do not invoke a skill that is already running
- Do not use this tool for built-in CLI commands (like /help, /clear, etc.)
</skills_instructions>
<available_skills>
{available_skills_xml}
</available_skills>"""


# ==================== 工具定义（纯 Python dict，与 1.json 完全一致） ====================

_SKILL_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "Skill",
        "description": _skill_description(),
        "parameters": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {
                    "type": "string",
                    "description": 'The skill name (no arguments). E.g., "pdf" or "xlsx"',
                }
            },
            "additionalProperties": False,
        },
    },
}

_GLOB_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "Glob",
        "description": "Fast file pattern matching tool that works with any codebase size\n\nUsage:\n  - Supports glob patterns like \"/*.js\" or \"src//*.ts\"\n  - Returns matching file paths sorted by modification time\n  - Use this tool when you need to find files by name patterns\n  - When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the `SearchCodebase` tool instead\n  - You can call multiple tools in a single response. It is always better to speculatively perform multiple searches in parallel if they are potentially useful.\n",
        "parameters": {
            "type": "object",
            "required": ["pattern"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": 'The directory to search in. If not specified, the current working directory will be used. Omit this field to use the default directory. DO NOT enter "undefined" or "null" - simply omit it for the default behavior. Must be a valid absolute directory path if provided.',
                },
                "pattern": {
                    "type": "string",
                    "description": "The glob pattern to match files against.",
                },
            },
        },
    },
}

_LS_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "LS",
        "description": "Lists files and directories in a given path.\nThe path parameter must be an absolute path, not a relative path.\nYou can optionally provide an array of glob patterns to ignore with the ignore parameter.\n",
        "parameters": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute path to the directory to list (must be absolute, not relative).",
                },
                "ignore": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of glob patterns to ignore.",
                },
            },
        },
    },
}

_GREP_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "Grep",
        "description": "A powerful search tool built on ripgrep\n\n  Usage:\n  - NEVER invoke `grep` or `rg` as a Bash command. The Grep tool has been optimized for correct permissions and access.\n  - Supports full regex syntax (e.g., \"log.*Error\", \"function\\s+\\w+\")\n  - Filter files with glob parameter (e.g., \"*.js\", \"**/*.tsx\") or type parameter (e.g., \"js\", \"py\", \"rust\")\n  - Output modes: \"content\" shows matching lines, \"files_with_matches\" shows only file paths (default), \"count\" shows match counts\n  - Pattern syntax: Uses ripgrep (not grep) - literal braces need escaping (use `interface\\{\\}` to find `interface{}` in Go code)\n  - Multiline matching: By default patterns match within single lines only. For cross-line patterns like `struct \\{[\\s\\S]*?field`, use `multiline: true`\n  - Prefer `SearchCodebase` tool when precise code keywords are missing\n",
        "parameters": {
            "type": "object",
            "required": ["pattern"],
            "properties": {
                "-A": {
                    "type": "integer",
                    "minimum": 0,
                    "description": 'Number of lines to show after each match (rg -A). Requires output_mode: "content", ignored otherwise.',
                },
                "-B": {
                    "type": "integer",
                    "minimum": 0,
                    "description": 'Number of lines to show before each match (rg -B). Requires output_mode: "content", ignored otherwise.',
                },
                "-C": {
                    "type": "integer",
                    "minimum": 0,
                    "description": 'Number of lines to show before and after each match (rg -C). Requires output_mode: "content", ignored otherwise.',
                },
                "-i": {
                    "type": "boolean",
                    "description": "Case insensitive search (rg -i)",
                },
                "-n": {
                    "type": "boolean",
                    "description": 'Show line numbers in output (rg -n). Requires output_mode: "content", ignored otherwise.',
                },
                "glob": {
                    "type": "string",
                    "description": 'Glob pattern to filter files (e.g. "*.js", "*.{ts,tsx}") - maps to rg --glob',
                },
                "path": {
                    "type": "string",
                    "description": "File or directory to search in (rg PATH). Defaults to current working directory.",
                },
                "type": {
                    "type": "string",
                    "description": "File type to search (rg --type). Common types: js, py, rust, go, java, etc. More efficient than include for standard file types.",
                },
                "offset": {
                    "type": "integer",
                    "minimum": 0,
                    "description": 'Skip first N lines/entries before applying head_limit, equivalent to "| tail -n +N | head -N". Works across all output modes. Defaults to 0.',
                },
                "pattern": {
                    "type": "string",
                    "description": "The regular expression pattern to search for in file contents",
                },
                "multiline": {
                    "type": "boolean",
                    "description": "Enable multiline mode where . matches newlines and patterns can span lines (rg -U --multiline-dotall). Default: false.",
                },
                "head_limit": {
                    "type": "integer",
                    "minimum": 0,
                    "description": 'Limit output to first N lines/entries, equivalent to "| head -N". Works across all output modes: content (limits output lines), files_with_matches (limits file paths), count (limits count entries). Defaults to 100.',
                },
                "output_mode": {
                    "enum": ["content", "files_with_matches", "count"],
                    "type": "string",
                    "description": 'Output mode: "content" shows matching lines (supports -A/-B/-C context, -n line numbers, head_limit), "files_with_matches" shows file paths (supports head_limit), "count" shows match counts (supports head_limit). Defaults to "files_with_matches".',
                },
            },
        },
    },
}

_READ_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "Read",
        "description": "Reads a file from the local filesystem. You can access any file directly by using this tool.\nAssume this tool is able to read all files on the machine. If the User provides a path to a file assume that path is valid. It is okay to read a file that does not exist; an error will be returned.\n\nUsage:\n  - The file_path parameter must be an absolute path, not a relative path\n  - You can optionally specify a line offset and limit (especially handy for long files)\n  - Results are returned using cat -n format, with line numbers starting at 1\n  -  When you already know which part of the file you need, only read that part. This can be important for larger files.\n  - You have the capability to call multiple tools in a single response. It is always better to speculatively read multiple files as a batch that are potentially useful.\n  - If you read a file that exists but has empty contents you will receive a system reminder warning in place of file contents.\n",
        "parameters": {
            "type": "object",
            "required": ["file_path", "limit"],
            "properties": {
                "limit": {
                    "type": "integer",
                    "format": "int32",
                    "maximum": 1000,
                    "minimum": 1,
                    "description": "The number of lines to read (must be at least 1, cannot be negative). This parameter is required and controls how many lines to read from the file.",
                },
                "offset": {
                    "type": "integer",
                    "format": "int32",
                    "minimum": 1,
                    "description": "The line number to start reading from (must be at least 1). Only provide if the file is too large to read at once.",
                },
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to read.",
                },
            },
        },
    },
}

_RUNCOMMAND_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "RunCommand",
        "description": "Execute a command in a terminal session on behalf of the user.\nEnsure the command is compatible with the current operating system (macos).\n\n\n\nIMPORTANT: This tool is for terminal operations like git, npm, docker, build scripts, etc. DO NOT use it for file operations (reading, writing, editing, searching, finding files) — use the specialized tools for these instead.\n\nBefore executing the command, follow these steps:\n1. Directory Verification:\n  - If the command creates new directories or files, first verify the parent directory exists.\n  - Use the `cwd` parameter to specify the working directory rather than prepending `cd`.\n\n2. Command Execution:\n  - Always quote file paths that contain spaces with double quotes (e.g., cd \"path with spaces/file.txt\").\n  - You MUST avoid generating interactive commands unless the command only supports interactive input. For example, run `npm create vite@latest . -- --template react` instead of `npm create vite@latest .`.\n\nUsage notes:\n  - Terminals are stateful across sequential calls. Current working directory, environment variables, and state persist between calls within the same terminal.\n  - For performance, prefer reusing existing idle terminals. The system will automatically find and reuse an idle AI terminal when `target_terminal` is not specified.\n  - Commands will be run with PAGER=cat. You may want to limit the length of output for commands that usually rely on paging and may contain very long output (e.g. for git log, use git log -n <N> ; for man ls, man ls | head -n <N>).\n  - VERY IMPORTANT: You MUST avoid using search commands like `find` and `grep`. Use Grep, Glob,SearchCodebase tools instead. You MUST avoid read commands like `cat`, `head`, `tail`. Use the Read tool instead. Avoid editing files with `sed` and `awk`. Use the Edit tool instead.\n  - If you need to observe real-time output from a non-blocking command (blocking: false), use the CheckCommandStatus tool with the command's ID. Do not re-run the command — CheckCommandStatus lets you retrieve the latest output on demand.\n  - To stop a running command, use the StopCommand tool with the command's ID. Do not use `kill`, `pkill`, or other shell commands to terminate processes — StopCommand is the dedicated way.\n  - When issuing multiple commands:\n    - If the commands are independent and can run in parallel, make multiple RunCommand tool calls in a single message. For example, if you need to run \"git status\" and \"git diff\", send a single message with two RunCommand tool calls in parallel.\n    - If the commands depend on each other and must run sequentially, use a single RunCommand call with '&&' to chain them together (e.g., `git add . && git commit -m \"message\" && git push`). For instance, if one operation must complete before another starts (like mkdir before cp,Write before RunCommand for git operations, or git add before git commit), run these operations sequentially instead.\n    - Use ';' only when you need to run commands sequentially but don't care if earlier commands fail\n    - DO NOT use newlines to separate commands (newlines are ok in quoted strings)\n\n### Git Safety Protocol:\n  - NEVER update the git config\n  - NEVER run destructive git commands (push --force, reset --hard, checkout ., restore ., clean -f, branch -D) unless the user explicitly requests these actions. Taking unauthorized destructive actions is unhelpful and can result in lost work, so it's best to ONLY run these commands when given direct instructions \n  - NEVER run force push to main/master, warn the user if they request it\n  - When staging files, prefer adding specific files by name rather than using \"git add -A\" or \"git add .\", which can accidentally include sensitive files (.env, credentials) or large binaries\n  - NEVER commit changes unless the user explicitly asks you to. It is VERY IMPORTANT to only commit when explicitly asked, otherwise the user will feel that you are being too proactive\n\n### Committing changes with git\n\nOnly create commits when requested by the user. If unclear, ask first. When the user asks you to create a new git commit, follow these steps carefully:\n\nYou can call multiple tools in a single response. When multiple independent pieces of information are requested and all commands are likely to succeed, run multiple tool calls in parallel for optimal performance. The numbered steps below indicate which commands should be batched in parallel.\n\n1. Run the following commands in parallel, each using the RunCommand tool:\n  - Run a git status command to see all untracked files. IMPORTANT: Never use the -uall flag as it can cause memory issues on large repos.\n  - Run a git diff command to see both staged and unstaged changes that will be committed.\n  - Run a git log command to see recent commit messages, so that you can follow this repository's commit message style.\n2. Analyze all staged changes (both previously staged and newly added) and draft a commit message:\n  - Summarize the nature of the changes (eg. new feature, enhancement to an existing feature, bug fix, refactoring, test, docs, etc.). Ensure the message accurately reflects the changes and their purpose (i.e. \"add\" means a wholly new feature, \"update\" means an enhancement to an existing feature, \"fix\" means a bug fix, etc.).\n  - Do not commit files that likely contain secrets (.env, credentials.json, etc). Warn the user if they specifically request to commit those files\n  - Draft a concise (1-2 sentences) commit message that focuses on the \"why\" rather than the \"what\"\n  - Ensure it accurately reflects the changes and their purpose\n3. Run the following commands in parallel:\n  - Add relevant untracked files to the staging area.\n  - Run git status after the commit completes to verify success.\n  Note: git status depends on the commit completing, so run it sequentially after the commit.\n\nImportant notes:\n- NEVER run additional commands to read or explore code, besides git  commands\n- NEVER use the TodoWrite or Task tools\n- DO NOT push to the remote repository unless the user explicitly asks you to do so\n- IMPORTANT: Never use git commands with the -i flag (like git rebase -i or git add -i) since they require interactive input which is not supported.\n- IMPORTANT: Do not use --no-edit with git rebase commands, as the --no-edit flag is not a valid option for git rebase.\n- If there are no changes to commit (i.e., no untracked files and no modifications), do not create an empty commit\n- In order to ensure good formatting, ALWAYS pass the commit message via a HEREDOC, a la this example:\n<example>\ngit commit -m \"$(cat <<'EOF'\n  Commit message here.\n\n  EOF\n  )\"\n</example>\n\n### Pushing changes to remote\n\nWhen the user asks you to push changes, follow these steps:\n\n1. Run the following commands in parallel to understand the current state:\n  - `git status` to see all untracked and modified files (never use the -uall flag)\n  - `git log --oneline -5` to see recent commits\n  - `git branch -vv` to check if the current branch tracks a remote and is up to date\n\n2. Based on the results:\n  - If there are uncommitted changes, ask the user whether to commit first (do NOT commit automatically unless explicitly requested)\n  - If the branch has no upstream, use `git push -u origin <branch>` to set tracking\n  - If the branch already tracks a remote, use `git push`\n\nImportant:\n- NEVER use `git push --force` or `git push --force-with-lease` unless the user explicitly requests it\n- NEVER push to main/master directly — warn the user if they request it\n- If the push fails due to remote changes, suggest `git pull --rebase` first rather than force pushing\n- DO NOT use the TodoWrite or Task tools\n- Return merge request/pr/pull request link if available",
        "parameters": {
            "type": "object",
            "required": ["command", "blocking", "requires_approval"],
            "properties": {
                "cwd": {
                    "type": "string",
                    "description": "The working directory to run the command in, the value MUST be absolute path, if not provided, it will be the current working directory.",
                },
                "command": {
                    "type": "string",
                    "description": "The terminal command to execute.",
                },
                "blocking": {
                    "type": "boolean",
                    "description": "Set to `false` ONLY for web_server or long_running_process command types. Set to `true` for all other cases.\n",
                },
                "command_type": {
                    "type": "string",
                    "description": "Classify the command type BEFORE deciding [blocking]. Available types: [web_server, long_running_process, short_running_process, other].\n",
                },
                "target_terminal": {
                    "type": "string",
                    "description": "The target terminal for command execution. Can be a terminal id (from <available_terminal/> or previous <toolcall_result/>), or 'new' to create a new terminal. If not specified, the system will automatically reuse an idle AI terminal or create a new one if none is available. For performance, prefer reusing existing idle terminals.",
                },
                "requires_approval": {
                    "type": "boolean",
                    "description": "Whether the user must approval the command before it is executed. Set to 'false' for safe operations like read/write files/directories, create/initialize/build projects, install project dependencies, running development servers.\n",
                },
                "wait_ms_before_async": {
                    "type": "integer",
                    "format": "uint",
                    "minimum": 0,
                    "description": "This configuration applies only when [blocking] is set to false.\nIt defines the number of milliseconds to pause after initiating the command before letting it proceed in full asynchronous mode.\nThis delay is beneficial for commands that are meant to run asynchronously but might fail almost immediately with an error; the wait allows you to detect and observe any errors that occur during this initial period.\nIf you prefer not to wait, set this value to 0.\n",
                },
            },
        },
    },
}

_TODOWRITE_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "TodoWrite",
        "description": "Use this tool to create and manage a structured task list for your current coding session. This helps track progress, organize complex tasks, and demonstrate thoroughness to the user.\nNote: Other than when first creating todos, don't tell the user you're updating todos, just do it.\n### When to Use\nUse for complex tasks with 3+ distinct steps, or when the user explicitly requests a todo list.\nSkip for simple tasks (< 3 steps) or purely conversational requests.\nDon't add a \"test the change\" task unless the user asks for it.\n### merge Parameter\n- merge=false: Replace the entire todo list. Use when creating a fresh plan.\n- merge=true: Merge into the existing list by id. Only id and changed fields are required for updates; all fields required for new items.\n### Task States & Display Order\n- pending / in_progress / completed\n- Only ONE task may be in_progress at a time.\n- Mark tasks complete IMMEDIATELY after finishing, before starting the next.\n- Todos are displayed sorted by: status (in_progress > pending > completed), then priority (high > medium > low), then creation time. Assign priority based on actual importance to the user.\n### Summary Field\nInclude `summary` only when marking tasks as completed. Describe what was done and the outcomes.\n### Parallel Tool Calls\n- Prefer creating the first todo as in_progress.\n- Start working on todos by using tool calls in the same tool call batch as the todo write.\n- Batch todo updates with other tool calls for better latency and lower costs for the user.\n### IMPORTANT\n- When the user sends a new task that supersedes the current todo_list, use merge=false to replace the todo list instead of merging.\n- Do not end your turn before all todos are completed.\n- All required fields (content, status, id, priority) must be provided when creating new items. When updating existing items via merge=true, content and priority can be omitted to preserve their current values.  \n",
        "parameters": {
            "type": "object",
            "required": ["todos", "merge"],
            "properties": {
                "merge": {
                    "type": "boolean",
                    "description": "Whether to merge the todos with the existing todos. If true, the todos will be merged into the existing todos based on the id field. You can leave unchanged properties undefined. If false, the new todos will replace the existing todos.",
                },
                "todos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["content", "status", "id", "priority"],
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Unique identifier for the todo item",
                            },
                            "status": {
                                "enum": ["pending", "in_progress", "completed"],
                                "type": "string",
                                "description": "The current status of the todo item",
                            },
                            "content": {
                                "type": "string",
                                "description": "The description/content of the todo item. Make sure the language of todo item content is consistent with the language of <user_input>!",
                            },
                            "priority": {
                                "enum": ["high", "medium", "low"],
                                "type": "string",
                            },
                        },
                    },
                    "maxItems": 10,
                    "minItems": 3,
                    "description": "Array of todo items to write to the workspace",
                },
            },
        },
    },
}

_SEARCHREPLACE_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "SearchReplace",
        "description": "You can use this tool to edit file. You should specify the following arguments before the others: `file_path`\n\nWhen you choose to use this tool to edit a existing file, you MUST follow the *SEARCH/REPLACE* Rules to set the `old_str` and `new_str` parameters:\n\n1. The `old_str` is the SEARCH section that should be a contiguous chunk of lines to search for in the existing source code.\n2. The `new_str` is the REPLACE section that should be lines to replace into the source code.\n3. The REPLACE section MUST be different from the SEARCH section.\n\nThis tool will *only* replace the first match occurrence of the SEARCH section.\nInclude enough lines in the SEARCH section to uniquely match the set of lines that need to change.\n\nKeep your SEARCH and REPLACE sections concise.\nInclude just the changing lines, and a few surrounding lines if needed for uniqueness.\nDo not include long runs of unchanging lines in your SEARCH and REPLACE sections.\n\nOnly create SEARCH and REPLACE sections for file that the user has added to the chat!\n\nIf you want to move code within a file, you need to make two separate edit operations: delete the original code chunk and then insert it in another location.\n",
        "parameters": {
            "type": "object",
            "required": ["file_path", "old_str", "new_str"],
            "properties": {
                "new_str": {
                    "type": "string",
                    "description": "The REPLACE section, the lines to replace into the source code.",
                },
                "old_str": {
                    "type": "string",
                    "description": "The SEARCH section, a contiguous chunk of lines to search for in the existing source code.",
                },
                "file_path": {
                    "type": "string",
                    "description": "The file path, you MUST set file path to absolute path.",
                },
            },
        },
    },
}

_WRITE_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "Write",
        "description": "Writes a file to the local filesystem.\n\nUsage:\n- This tool will overwrite the existing file if there is one at the provided path.\n- If this is an existing file, you MUST use the Read tool first to read the file's contents. This tool will fail if you did not read the file first.\n- ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.\n- NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.\n- Only use emojis if the user explicitly requests it. Avoid writing emojis to files unless asked.\n",
        "parameters": {
            "type": "object",
            "required": ["file_path", "content"],
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The content to write to the file",
                },
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to write (must be absolute, not relative)",
                },
            },
            "additionalProperties": False,
        },
    },
}

_DELETEFILE_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "DeleteFile",
        "description": "You can use this tool to delete files, you can delete multi files in one toolcall, and you MUST make sure the files is exist before deleting.\nWhen you need to delete file, you MUST use this tool to delete file instead of using shell.\n",
        "parameters": {
            "type": "object",
            "required": ["file_paths"],
            "properties": {
                "file_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "The list of file paths you want to delete, you MUST set file path to absolute path.",
                },
            },
        },
    },
}

_ASKUSERQUESTION_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "AskUserQuestion",
        "description": "Use this tool when you need to ask the user questions during execution. \nThis allows you to: \n  1. Gather user preferences or requirements \n  2. Clarify ambiguous instructions \n  3. Get decisions on implementation choices as you work \n  4. Offer choices to the user about what direction to take. \nUsage notes: \n  - IMPORTANT: When the user explicitly invites discussion (e.g., \"discuss\", \"decide together\", \"let's talk about\", \"讨论一下\", \"你觉得呢\") AND the request has not yet converged to a specific action, use this tool proactively to structure the discussion into clear options before producing a final output.\n  - Users will always be able to select \"Other\" to provide custom text input\n  - Use multiSelect: true to allow multiple answers to be selected for a question\n  - If you recommend a specific option, make that the first option in the list and add \"(Recommended)\" at the end of the label \n",
        "parameters": {
            "type": "object",
            "required": ["questions"],
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["question", "header", "options", "multiSelect"],
                        "properties": {
                            "header": {
                                "type": "string",
                                "description": "Very short label displayed as a chip/tag (max 12 chars). Examples: \"Auth method\", \"Library\", \"Approach\".",
                            },
                            "options": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["label", "description"],
                                    "properties": {
                                        "label": {
                                            "type": "string",
                                            "description": "The display text for this option that the user will see and select. Should be concise (1-5 words) and clearly describe the choice.",
                                        },
                                        "description": {
                                            "type": "string",
                                            "description": "Explanation of what this option means or what will happen if chosen. Useful for providing context about trade-offs or implications.",
                                        },
                                    },
                                },
                                "maxItems": 4,
                                "minItems": 2,
                                "description": "The available choices for this question. Must have 2-4 options. Each option should be a distinct, mutually exclusive choice (unless multiSelect is enabled). There should be no 'Other' option, that will be provided automatically.",
                            },
                            "question": {
                                "type": "string",
                                "description": "The complete question to ask the user. Should be clear, specific, and end with a question mark. Example: \"Which library should we use for date formatting?\" If multiSelect is true, phrase it accordingly, e.g. \"Which features do you want to enable?\"",
                            },
                            "multiSelect": {
                                "type": "boolean",
                                "default": False,
                                "description": "Set to true to allow the user to select multiple options instead of just one. Use when choices are not mutually exclusive.",
                            },
                        },
                    },
                    "maxItems": 4,
                    "minItems": 1,
                    "description": "Questions to ask the user (1-4 questions)",
                },
            },
        },
    },
}


# ==================== 工具定义入口 ====================

def get_tool_definitions() -> List[Dict[str, Any]]:
    """获取工具定义（与 1.json 完全一致）"""
    return [
        _SKILL_TOOL,
        # _GLOB_TOOL,
        # _LS_TOOL,
        # _GREP_TOOL,
        # _READ_TOOL,
        _RUNCOMMAND_TOOL,
        _TODOWRITE_TOOL,
        # _SEARCHREPLACE_TOOL,
        # _WRITE_TOOL,
        # _DELETEFILE_TOOL,
        _ASKUSERQUESTION_TOOL,
    ]
