"""
工具执行器模块 - 与 1.json 规范一致

工具列表：
1. Skill - 执行技能
2. Glob - 文件模式匹配
3. LS - 列出目录
4. Grep - 文本搜索
5. Read - 读取文件
6. RunCommand - 执行命令
7. TodoWrite - 任务管理（支持并发控制）

所有工具都支持 parallel 参数控制并发执行
"""

import glob as glob_module
import fnmatch
import json
import subprocess
import uuid
import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from app.services.agent.skill_loader import load_skill
from app.log import logger


def format_tool_result(status: str, result: Any, is_json: bool = True) -> str:
    """格式化工具执行结果 - 与 1.json 规范一致

    Args:
        status: 执行状态 (done, error, running)
        result: 执行结果，可以是字典、字符串或其他类型
        is_json: 是否将结果格式化为 JSON，默认为 True

    Returns:
        格式化的工具结果字符串，包含 <toolcall_status> 和 <toolcall_result> 标签
    """
    if is_json and isinstance(result, dict):
        result_str = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        result_str = str(result)

    return f"""<toolcall_status>{status}</toolcall_status>
<toolcall_result>
{result_str}
</toolcall_result>"""


def format_todo_write_result(status: str, todos: List[Dict[str, Any]]) -> str:
    """格式化 TodoWrite 工具执行结果 - 与 1.json 完全一致

    Args:
        status: 执行状态 (done, error)
        todos: 任务列表

    Returns:
        格式化的 TodoWrite 结果字符串，包含 system-reminder
    """
    todos_json = json.dumps(todos, ensure_ascii=False)

    return f"""<toolcall_status>{status}</toolcall_status>
<toolcall_result>
Todos have been modified successfully. Ensure you continue to use the todo list to track your progress. Please proceed with your current tasks if applicable

<system-reminder>
Your todo list has changed. DO NOT mention this explicitly to the user. Here are the latest contents of your todo list:

{{"todos":{todos_json}}}.
</system-reminder>
</toolcall_result>"""


# ==================== 并发控制管理器 ====================

class ConcurrencyManager:
    """全局并发控制管理器

    管理所有工具的并发执行，支持大模型通过 parallel 参数控制并发度
    """

    def __init__(self):
        # 每个对话的并发限制配置
        self._max_parallel: Dict[str, int] = {}
        # 每个对话的当前执行计数
        self._running_count: Dict[str, int] = {}
        # 每个对话的待执行队列
        self._task_queues: Dict[str, asyncio.Queue] = {}
        # 线程池执行器（用于同步操作）
        self._executor = ThreadPoolExecutor(max_workers=20)

    def set_max_parallel(self, conversation_id: str, parallel: int):
        """设置对话的最大并发数"""
        self._max_parallel[conversation_id] = max(1, min(10, parallel))

    def get_max_parallel(self, conversation_id: str) -> int:
        """获取对话的最大并发数"""
        return self._max_parallel.get(conversation_id, 3)

    def can_execute(self, conversation_id: str) -> bool:
        """检查是否可以执行新任务"""
        current = self._running_count.get(conversation_id, 0)
        max_parallel = self.get_max_parallel(conversation_id)
        return current < max_parallel

    def start_execution(self, conversation_id: str) -> bool:
        """开始执行任务，增加计数"""
        if self.can_execute(conversation_id):
            self._running_count[conversation_id] = self._running_count.get(conversation_id, 0) + 1
            return True
        return False

    def end_execution(self, conversation_id: str):
        """结束执行任务，减少计数"""
        current = self._running_count.get(conversation_id, 0)
        if current > 0:
            self._running_count[conversation_id] = current - 1

    def get_executor(self) -> ThreadPoolExecutor:
        """获取线程池执行器"""
        return self._executor

    def get_status(self, conversation_id: str) -> Dict[str, Any]:
        """获取并发状态"""
        return {
            "max_parallel": self.get_max_parallel(conversation_id),
            "running": self._running_count.get(conversation_id, 0),
            "can_execute": self.can_execute(conversation_id)
        }


# 全局并发管理器
concurrency_manager = ConcurrencyManager()


# ==================== Skill 执行器 ====================

class SkillExecutor:
    """Skill 执行器 - 执行 autofill-form 等 Skill"""

    def __init__(self):
        self._active_skills: Dict[str, Dict[str, Any]] = {}  # conversation_id -> skill context

    def activate_skill(self, conversation_id: str, skill_name: str) -> bool:
        """激活指定的 Skill"""
        skill_config = load_skill(skill_name)
        if skill_config:
            self._active_skills[conversation_id] = {
                "name": skill_name,
                "config": skill_config,
                "step": 0,
                "data": {}
            }
            return True
        return False

    def get_active_skill(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """获取当前激活的 Skill"""
        return self._active_skills.get(conversation_id)

    def is_skill_active(self, conversation_id: str) -> bool:
        """检查是否有 Skill 处于激活状态"""
        return conversation_id in self._active_skills

    def deactivate_skill(self, conversation_id: str):
        """停用 Skill"""
        if conversation_id in self._active_skills:
            del self._active_skills[conversation_id]

    def get_skill_system_prompt(self, conversation_id: str) -> Optional[str]:
        """获取当前 Skill 的系统提示词"""
        skill_ctx = self._active_skills.get(conversation_id)
        if skill_ctx:
            return skill_ctx["config"]["content"]
        return None


# 全局 Skill 执行器
skill_executor = SkillExecutor()


# ==================== 命令管理器 ====================

class CommandManager:
    """管理异步命令执行"""

    def __init__(self):
        self._commands: Dict[str, Dict[str, Any]] = {}

    def create_command(self, command: str, cwd: Optional[str] = None,
                       blocking: bool = True, wait_ms: int = 0) -> str:
        """创建命令记录"""
        command_id = str(uuid.uuid4())
        self._commands[command_id] = {
            "id": command_id,
            "command": command,
            "cwd": cwd,
            "blocking": blocking,
            "wait_ms": wait_ms,
            "status": "created",
            "pid": None,
            "output": "",
            "error": "",
            "exit_code": None,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
        }
        return command_id

    def get_command(self, command_id: str) -> Optional[Dict[str, Any]]:
        """获取命令信息"""
        return self._commands.get(command_id)

    def update_command(self, command_id: str, **kwargs) -> None:
        """更新命令信息"""
        if command_id in self._commands:
            self._commands[command_id].update(kwargs)


# 全局命令管理器
command_manager = CommandManager()


# ==================== Todo 管理器 ====================

class TodoManager:
    """管理任务列表，支持并发控制"""

    def __init__(self):
        self._todos: Dict[str, Dict[str, Any]] = {}  # conversation_id -> todo list
        self._max_parallel: Dict[str, int] = {}  # conversation_id -> max parallel tasks

    def get_todos(self, conversation_id: str) -> List[Dict[str, Any]]:
        """获取指定对话的任务列表"""
        return self._todos.get(conversation_id, {}).get("todos", [])

    def get_max_parallel(self, conversation_id: str) -> int:
        """获取指定对话的最大并发数"""
        return self._max_parallel.get(conversation_id, 3)

    def write_todos(self, conversation_id: str, todos: List[Dict[str, Any]], merge: bool = False, parallel: int = 3) -> Dict[str, Any]:
        """写入或更新任务列表

        Args:
            conversation_id: 对话ID
            todos: 任务列表
            merge: 是否合并到现有列表
            parallel: 最大并发数

        Returns:
            更新后的任务列表信息
        """
        # 验证并规范化任务数据
        validated_todos = []
        for todo in todos:
            validated_todo = {
                "id": todo.get("id", str(uuid.uuid4())),
                "content": todo.get("content", ""),
                "status": todo.get("status", "pending"),
                "priority": todo.get("priority", "medium")
            }
            validated_todos.append(validated_todo)

        # 限制并发数范围
        parallel = max(1, min(5, parallel))
        self._max_parallel[conversation_id] = parallel

        if merge and conversation_id in self._todos:
            # 合并模式：更新现有任务或添加新任务
            existing_todos = self._todos[conversation_id]["todos"]
            existing_ids = {t["id"] for t in existing_todos}

            for todo in validated_todos:
                if todo["id"] in existing_ids:
                    # 更新现有任务
                    for i, existing in enumerate(existing_todos):
                        if existing["id"] == todo["id"]:
                            # 只更新提供的字段
                            if "content" in todo:
                                existing_todos[i]["content"] = todo["content"]
                            if "status" in todo:
                                existing_todos[i]["status"] = todo["status"]
                            if "priority" in todo:
                                existing_todos[i]["priority"] = todo["priority"]
                            break
                else:
                    # 添加新任务
                    existing_todos.append(todo)

            # 限制任务数量
            if len(existing_todos) > 10:
                existing_todos = existing_todos[:10]

            self._todos[conversation_id] = {
                "todos": existing_todos,
                "updated_at": datetime.now().isoformat(),
                "parallel": parallel
            }
        else:
            # 替换模式
            self._todos[conversation_id] = {
                "todos": validated_todos,
                "updated_at": datetime.now().isoformat(),
                "parallel": parallel
            }

        return {
            "todos": self._todos[conversation_id]["todos"],
            "count": len(self._todos[conversation_id]["todos"]),
            "parallel": parallel,
            "in_progress": len([t for t in self._todos[conversation_id]["todos"] if t["status"] == "in_progress"]),
            "completed": len([t for t in self._todos[conversation_id]["todos"] if t["status"] == "completed"]),
            "pending": len([t for t in self._todos[conversation_id]["todos"] if t["status"] == "pending"])
        }

    def can_start_new_task(self, conversation_id: str) -> bool:
        """检查是否可以开始新任务（基于并发控制）"""
        todos = self.get_todos(conversation_id)
        in_progress = len([t for t in todos if t["status"] == "in_progress"])
        return in_progress < self.get_max_parallel(conversation_id)

    def update_todo_status(self, conversation_id: str, todo_id: str, status: str) -> bool:
        """更新单个任务状态"""
        if conversation_id not in self._todos:
            return False

        for todo in self._todos[conversation_id]["todos"]:
            if todo["id"] == todo_id:
                todo["status"] = status
                self._todos[conversation_id]["updated_at"] = datetime.now().isoformat()
                return True
        return False


# 全局 Todo 管理器
todo_manager = TodoManager()


# ==================== 工具执行函数 ====================

async def execute_skill(name: str = None, conversation_id: str = "default", **kwargs) -> str:
    """执行 Skill 工具

    当 Agent 调用 Skill 工具时，加载对应的 Skill 并返回其内容。
    按照 1.json 规范，Skill 内容直接通过 tool 结果返回给大模型。

    Args:
        name: Skill 名称
        conversation_id: 对话ID
        **kwargs: 其他可能的参数

    Returns:
        格式化的工具结果字符串，包含 Skill 路径和内容
    """
    # 处理可能的参数嵌套情况
    if name is None and 'kwargs' in kwargs:
        nested = kwargs.get('kwargs', {})
        if isinstance(nested, dict):
            name = nested.get('name') or nested.get('skill_name')

    # 如果 name 仍然为空，尝试从其他参数获取
    if name is None:
        name = kwargs.get('skill_name') or kwargs.get('skill')

    if not name:
        return format_tool_result("error", {
            "type": "skill_error",
            "error": "Skill name is required. Please provide the skill name to invoke."
        })

    # 加载 Skill
    skill_config = load_skill(name)

    if skill_config:
        # 构建 Skill 文件路径
        skill_path = os.path.join(".trae", "skills", name, "SKILL.md")

        # 按照 1.json 规范，Skill 直接返回 markdown 内容
        skill_content = skill_config.get("content", "")
        result_text = f"""**Skill Path:** {skill_path}

{skill_content}"""
        return format_tool_result("done", result_text, is_json=False)
    else:
        return format_tool_result("error", f"Failed to load skill: {name}", is_json=False)


async def execute_glob(pattern: str, path: Optional[str] = None, **kwargs) -> str:
    """执行 Glob 工具 - 与 1.json 一致"""
    search_path = path or os.getcwd()
    full_pattern = os.path.join(search_path, pattern) if not pattern.startswith("/") else pattern

    try:
        files = glob_module.glob(full_pattern, recursive=True)
        # 按修改时间排序
        files.sort(key=lambda x: os.path.getmtime(x) if os.path.exists(x) else 0, reverse=True)
        return format_tool_result("done", {
            "files": files[:100],  # 限制返回数量
            "count": len(files)
        })
    except Exception as e:
        return format_tool_result("error", {"error": str(e)})


async def execute_ls(path: str, ignore: Optional[List[str]] = None, **kwargs) -> str:
    """执行 LS 工具 - 与 1.json 一致"""
    try:
        items = []
        for item in os.listdir(path):
            # 检查是否被忽略
            if ignore:
                skip = False
                for pattern in ignore:
                    if fnmatch.fnmatch(item, pattern):
                        skip = True
                        break
                if skip:
                    continue

            full_path = os.path.join(path, item)
            items.append({
                "name": item,
                "path": full_path,
                "type": "directory" if os.path.isdir(full_path) else "file"
            })

        return format_tool_result("done", {
            "path": path,
            "items": items
        })
    except Exception as e:
        return format_tool_result("error", {"error": str(e)})


async def execute_grep(pattern: str, path: Optional[str] = None, glob: Optional[str] = None,
                       type: Optional[str] = None, output_mode: str = "files_with_matches",
                       head_limit: int = 100, offset: int = 0, multiline: bool = False,
                       A: Optional[int] = None, B: Optional[int] = None, C: Optional[int] = None,
                       i: bool = False, n: bool = False, **kwargs) -> str:
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


async def execute_read(file_path: str, limit: int, offset: Optional[int] = None, **kwargs) -> str:
    """执行 Read 工具 - 与 1.json 一致
    
    返回文件内容（文本格式），与 cat -n 格式一致
    """
    try:
        if not os.path.exists(file_path):
            return format_tool_result("error", f"File not found: {file_path}", is_json=False)

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        start = (offset - 1) if offset else 0
        end = start + limit
        selected_lines = lines[start:end]

        # 添加行号，与 cat -n 格式一致
        content = "".join(f"{start + i + 1:6}\t{line}" for i, line in enumerate(selected_lines))

        # 返回纯文本内容
        return format_tool_result("done", content, is_json=False)
    except Exception as e:
        return format_tool_result("error", str(e), is_json=False)


async def execute_run_command(command: str, cwd: Optional[str] = None, blocking: bool = True,
                              command_type: Optional[str] = None, requires_approval: bool = False,
                              wait_ms_before_async: int = 0, **kwargs) -> str:
    """执行 RunCommand 工具 - 与 1.json 一致"""
    work_dir = cwd or os.getcwd()

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

        result = subprocess.run(
            command,
            shell=True,
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


async def execute_todo_write(todos: List[Dict[str, Any]], merge: bool = False,
                             conversation_id: str = "default", **kwargs) -> str:
    """执行 TodoWrite 工具 - 与 1.json 一致

    支持复杂任务管理，包括：
    - 任务列表的创建和更新
    - 任务状态管理

    Args:
        todos: 任务列表数组
        merge: 是否合并到现有列表
        conversation_id: 对话ID
        **kwargs: 其他参数

    Returns:
        JSON 格式的执行结果
    """
    try:
        # 验证任务数量
        # merge=false 时要求至少 3 个（新建完整计划）
        # merge=true 时允许至少 1 个（局部更新状态）
        min_items = 1 if merge else 3
        if not todos or len(todos) < min_items:
            return format_tool_result("error", {
                "error": f"At least {min_items} todos are required",
                "min_items": min_items,
                "provided": len(todos) if todos else 0
            })

        if len(todos) > 10:
            return format_tool_result("error", {
                "error": "At most 10 todos are allowed",
                "max_items": 10,
                "provided": len(todos)
            })

        # 验证每个任务项
        validated_todos = []
        for todo in todos:
            if not isinstance(todo, dict):
                return format_tool_result("error", {
                    "error": "Each todo must be an object",
                    "invalid_todo": str(todo)
                })

            validated_todo = {
                "id": todo.get("id", str(uuid.uuid4())),
                "content": todo.get("content", ""),
                "status": todo.get("status", "pending"),
                "priority": todo.get("priority", "medium")
            }
            validated_todos.append(validated_todo)

        # 写入任务列表
        result = todo_manager.write_todos(conversation_id, validated_todos, merge)

        return format_todo_write_result("done", validated_todos)

    except Exception as e:
        return format_tool_result("error", {"error": str(e)})


# 工具执行器映射
TOOL_EXECUTORS = {
    "Skill": execute_skill,
    "Glob": execute_glob,
    "LS": execute_ls,
    "Grep": execute_grep,
    "Read": execute_read,
    "RunCommand": execute_run_command,
    "TodoWrite": execute_todo_write,
}


async def execute_tool(tool_name: str, arguments: Dict[str, Any], conversation_id: str = "default") -> str:
    """执行指定工具 - 统一的工具执行入口

    Args:
        tool_name: 工具名称
        arguments: 工具参数
        conversation_id: 对话ID（用于 Skill 等需要上下文的工具）

    Returns:
        工具执行结果的 JSON 字符串
    """
    executor = TOOL_EXECUTORS.get(tool_name)

    if not executor:
        logger.error({
            "event": "tool_execute_unknown",
            "tool_name": tool_name
        })
        return format_tool_result("error", {
            "error": f"Unknown tool: {tool_name}"
        })

    try:
        # 确保 arguments 是字典
        if not isinstance(arguments, dict):
            logger.error({
                "event": "tool_execute_invalid_args",
                "tool_name": tool_name,
                "args_type": type(arguments).__name__,
                "arguments": str(arguments)
            })
            return format_tool_result("error", {
                "error": f"Invalid arguments type for {tool_name}: expected dict, got {type(arguments).__name__}",
                "hint": f"Please provide valid JSON arguments for the {tool_name} tool.",
                "received_arguments": str(arguments)
            })

        # 记录接收到的参数
        logger.info({
            "event": "tool_execute_start",
            "tool_name": tool_name,
            "conversation_id": conversation_id,
            "arguments": arguments
        })

        # 特殊处理需要 conversation_id 的工具
        if tool_name in ["Skill", "TodoWrite"]:
            arguments["conversation_id"] = conversation_id

        # 对于 Skill 工具，确保 name 参数存在
        if tool_name == "Skill":
            if "name" not in arguments or not arguments["name"]:
                logger.warning({
                    "event": "tool_execute_skill_missing_name",
                    "conversation_id": conversation_id,
                    "received_arguments": arguments
                })
                return format_tool_result("error", {
                    "error": "Skill name is required",
                    "hint": "Please provide the skill name in the 'name' parameter. Example: {\"name\": \"autofill-form\"}",
                    "received_arguments": str(arguments)
                })

        # 对于 RunCommand 工具，确保 command 参数存在
        if tool_name == "RunCommand":
            if "command" not in arguments or not arguments["command"]:
                logger.warning({
                    "event": "tool_execute_runcommand_missing_command",
                    "conversation_id": conversation_id,
                    "received_arguments": arguments
                })
                return format_tool_result("error", {
                    "error": "Command is required",
                    "hint": "Please provide the command to execute in the 'command' parameter. Example: {\"command\": \"python script.py\", \"blocking\": true, \"requires_approval\": false}",
                    "received_arguments": str(arguments),
                    "available_keys": list(arguments.keys()) if arguments else []
                })
            # 确保必需的布尔参数存在
            if "blocking" not in arguments:
                arguments["blocking"] = True
            if "requires_approval" not in arguments:
                arguments["requires_approval"] = False

        # 对于 TodoWrite 工具，确保 todos 参数存在
        if tool_name == "TodoWrite":
            if "todos" not in arguments or not arguments["todos"]:
                logger.warning({
                    "event": "tool_execute_todowrite_missing_todos",
                    "conversation_id": conversation_id
                })
                return format_tool_result("error", {
                    "error": "Todos list is required",
                    "hint": "Please provide a list of todos in the 'todos' parameter. Example: {\"todos\": [{\"id\": \"1\", \"content\": \"Task 1\", \"status\": \"pending\", \"priority\": \"high\"}], \"merge\": false}",
                    "received_arguments": str(arguments)
                })
            if "merge" not in arguments:
                arguments["merge"] = False

        result = await executor(**arguments)
        
        logger.info({
            "event": "tool_execute_complete",
            "tool_name": tool_name,
            "conversation_id": conversation_id,
            "result_preview": result[:200] if result else ""
        })
        
        return result
    except TypeError as e:
        # 处理参数缺失错误
        error_msg = str(e)
        logger.error({
            "event": "tool_execute_type_error",
            "tool_name": tool_name,
            "conversation_id": conversation_id,
            "error": error_msg,
            "received_arguments": str(arguments) if 'arguments' in dir() else "not available"
        })
        if "missing" in error_msg and "required" in error_msg:
            return format_tool_result("error", {
                "error": f"Missing required parameters for {tool_name}: {error_msg}",
                "hint": f"Please check the tool schema and provide all required parameters for {tool_name}.",
                "received_arguments": str(arguments) if 'arguments' in dir() else "not available"
            })
        return format_tool_result("error", {
            "error": f"Tool execution failed: {error_msg}",
            "received_arguments": str(arguments) if 'arguments' in dir() else "not available"
        })
    except Exception as e:
        logger.error({
            "event": "tool_execute_exception",
            "tool_name": tool_name,
            "conversation_id": conversation_id,
            "error": str(e),
            "received_arguments": str(arguments) if 'arguments' in dir() else "not available"
        })
        return format_tool_result("error", {
            "error": f"Tool execution failed: {str(e)}",
            "received_arguments": str(arguments) if 'arguments' in dir() else "not available"
        })
