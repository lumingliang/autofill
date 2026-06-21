"""
Todo 管理器 - 管理任务列表，支持并发控制
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List


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


# 全局 Todo 管理器实例
todo_manager = TodoManager()
