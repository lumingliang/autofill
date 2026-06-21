"""
TodoWrite 工具 - 任务管理
"""
import uuid
from typing import Any, Dict, List, Literal

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from app.services.agent.todo_manager import todo_manager
from app.services.agent.tool_executor import format_tool_result, format_todo_write_result


class TodoItem(BaseModel):
    id: str = Field(description="Unique identifier for the todo item")
    content: str = Field(description="The description/content of the todo item. Make sure the language of todo item\ncontent is consistent with the language of <user_input>!")
    status: Literal["pending", "in_progress", "completed"] = Field(description="The current status of the todo item")
    priority: Literal["high", "medium", "low"] = Field(description="The priority of the todo item")


class TodoWriteInput(BaseModel):
    merge: bool = Field(description="Whether to merge the todos with the existing todos. If true, the todos will be\nmerged into the existing todos based on the id field. You can leave unchanged\nproperties undefined. If false, the new todos will replace the existing todos.")
    todos: List[TodoItem] = Field(min_length=3, max_length=10, description="Array of todo items to write to the workspace")


async def execute_todo_write(todos: List[TodoItem], merge: bool, config: RunnableConfig = None) -> str:
    """执行 TodoWrite 工具 - 与 1.json 一致"""
    conversation_id = "default"
    if config and config.get("metadata"):
        context = config["metadata"].get("tool_context")
        if context:
            conversation_id = getattr(context, "session_id", "default")

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

        # 验证每个任务项（LangChain 已根据 TodoWriteInput 解析为 TodoItem 对象）
        validated_todos = []
        for todo in todos:
            validated_todo = {
                "id": getattr(todo, "id", None) or str(uuid.uuid4()),
                "content": getattr(todo, "content", "") or "",
                "status": getattr(todo, "status", "pending") or "pending",
                "priority": getattr(todo, "priority", "medium") or "medium"
            }
            validated_todos.append(validated_todo)

        # 写入任务列表
        todo_manager.write_todos(conversation_id, validated_todos, merge)

        return format_todo_write_result("done", validated_todos)

    except Exception as e:
        return format_tool_result("error", {"error": str(e)})


def get_todo_write_tool() -> BaseTool:
    return StructuredTool.from_function(
        name="TodoWrite",
        description="Use this tool to create and manage a structured task list for your current coding session. This helps track progress, organize complex tasks, and demonstrate thoroughness to the user.\nNote: Other than when first creating todos, don't tell the user you're updating todos, just do it.\n### When to Use\nUse for complex tasks with 3+ distinct steps, or when the user explicitly requests a todo list.\nSkip for simple tasks (< 3 steps) or purely conversational requests.\nDon't add a \"test the change\" task unless the user asks for it.\n### merge Parameter\n- merge=false: Replace the entire todo list. Use when creating a fresh plan.\n- merge=true: Merge into the existing list by id. Only id and changed fields are required for updates; all fields required for new items.\n### Task States & Display Order\n- pending / in_progress / completed\n- Only ONE task may be in_progress at a time.\n- Mark tasks complete IMMEDIATELY after finishing, before starting the next.\n- Todos are displayed sorted by: status (in_progress > pending > completed), then priority (high > medium > low), then creation time. Assign priority based on actual importance to the user.\n### Summary Field\nInclude `summary` only when marking tasks as completed. Describe what was done and the outcomes.\n### Parallel Tool Calls\n- Prefer creating the first todo as in_progress.\n- Start working on todos by using tool calls in the same tool call batch as the todo write.\n- Batch todo updates with other tool calls for better latency and lower costs for the user.\n### IMPORTANT\n- When the user sends a new task that supersedes the current todo_list, use merge=false to replace the todo list instead of merging.\n- Do not end your turn before all todos are completed.\n- All required fields (content, status, id, priority) must be provided when creating new items. When updating existing items via merge=true, content and priority can be omitted to preserve their current values.  \n",
        func=None,
        coroutine=execute_todo_write,
        args_schema=TodoWriteInput,
    )
