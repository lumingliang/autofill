"""
ToolRegistry - 统一工具注册表

支持按名称注册、查询、批量获取 LangChain Tool 实例。
"""
from typing import Dict, List, Optional

from langchain_core.tools import BaseTool

from app.services.agent.tools import (
    get_ask_user_question_tool,
    get_delete_file_tool,
    get_glob_tool,
    get_grep_tool,
    get_ls_tool,
    get_read_tool,
    get_run_command_tool,
    get_search_replace_tool,
    get_skill_tool,
    get_todo_write_tool,
    get_write_tool,
)


# 工具名 -> 工厂函数映射
_TOOL_FACTORIES = {
    "Skill": get_skill_tool,
    "Glob": get_glob_tool,
    "LS": get_ls_tool,
    "Grep": get_grep_tool,
    "Read": get_read_tool,
    "RunCommand": get_run_command_tool,
    "TodoWrite": get_todo_write_tool,
    "SearchReplace": get_search_replace_tool,
    "Write": get_write_tool,
    "DeleteFile": get_delete_file_tool,
    "AskUserQuestion": get_ask_user_question_tool,
}


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, name: str, tool: BaseTool) -> None:
        """注册单个工具"""
        self._tools[name] = tool

    def get(self, name: str, allowed_skills: Optional[List[str]] = None) -> BaseTool:
        """按名称获取工具实例

        Args:
            name: 工具名
            allowed_skills: Skill 工具需要传入授权 Skill 列表

        Returns:
            BaseTool 实例

        Raises:
            KeyError: 工具未注册
        """
        if name == "Skill":
            return get_skill_tool(allowed_skills)
        if name not in self._tools:
            raise KeyError(f"Tool not registered: {name}")
        return self._tools[name]

    def get_many(self, names: List[str], allowed_skills: Optional[List[str]] = None) -> List[BaseTool]:
        """批量获取工具实例"""
        return [self.get(name, allowed_skills=allowed_skills) for name in names]

    def list_names(self) -> List[str]:
        """列出所有已注册工具名"""
        return list(self._tools.keys())

    def has(self, name: str) -> bool:
        """检查工具是否已注册"""
        return name in self._tools or name == "Skill"


def _build_default_registry() -> ToolRegistry:
    """构建默认工具注册表"""
    registry = ToolRegistry()
    for name, factory in _TOOL_FACTORIES.items():
        if name == "Skill":
            continue
        registry.register(name, factory())
    return registry


# 全局默认工具注册表实例
_default_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """获取全局默认工具注册表（懒加载）"""
    global _default_tool_registry
    if _default_tool_registry is None:
        _default_tool_registry = _build_default_registry()
    return _default_tool_registry
