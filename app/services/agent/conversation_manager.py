"""
ConversationManager - 对话历史管理器

按 (session_id, agent_name, tenant_id) 维度隔离会话历史。
默认存储在进程内存中，预留持久化接入点。
"""
from typing import Dict, List, Optional, Tuple

from langchain_core.messages import BaseMessage, SystemMessage


class ConversationManager:
    """对话上下文管理器 - 管理多轮对话历史"""

    def __init__(self, max_history: int = 20):
        self._conversations: Dict[Tuple[str, str, str], List[BaseMessage]] = {}
        self._max_history = max_history

    def _key(self, session_id: str, agent_name: str, tenant_id: str) -> Tuple[str, str, str]:
        return (session_id, agent_name, tenant_id)

    def get_or_create(self, session_id: str, agent_name: str, tenant_id: str) -> List[BaseMessage]:
        """获取或创建对话"""
        key = self._key(session_id, agent_name, tenant_id)
        if key not in self._conversations:
            self._conversations[key] = []
        return self._conversations[key]

    def add_message(self, session_id: str, agent_name: str, tenant_id: str, message: BaseMessage) -> None:
        """添加消息到对话历史"""
        self.add_messages(session_id, agent_name, tenant_id, [message])

    def add_messages(self, session_id: str, agent_name: str, tenant_id: str, messages: List[BaseMessage]) -> None:
        """批量添加消息到对话历史并触发截断"""
        history = self.get_or_create(session_id, agent_name, tenant_id)
        history.extend(messages)

        # 限制历史长度
        if len(history) > self._max_history:
            # 保留系统消息和最近的对话
            system_msgs = [m for m in history if isinstance(m, SystemMessage)]
            other_msgs = [m for m in history if not isinstance(m, SystemMessage)]
            other_msgs = other_msgs[-(self._max_history - len(system_msgs)):]
            self._conversations[self._key(session_id, agent_name, tenant_id)] = system_msgs + other_msgs

    def clear(self, session_id: str, agent_name: str, tenant_id: str) -> None:
        """清空对话"""
        key = self._key(session_id, agent_name, tenant_id)
        if key in self._conversations:
            del self._conversations[key]

    def get_history(self, session_id: str, agent_name: str, tenant_id: str) -> List[BaseMessage]:
        """获取对话历史副本"""
        return list(self.get_or_create(session_id, agent_name, tenant_id))

    def set_history(self, session_id: str, agent_name: str, tenant_id: str, history: List[BaseMessage]) -> None:
        """设置对话历史（预留持久化恢复使用）"""
        self._conversations[self._key(session_id, agent_name, tenant_id)] = history
