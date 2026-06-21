"""
命令管理器 - 管理异步命令执行
"""
import uuid
from datetime import datetime
from typing import Any, Dict, Optional


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


# 全局命令管理器实例
command_manager = CommandManager()
