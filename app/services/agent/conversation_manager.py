"""
ConversationManager - 对话历史管理器

每个 AgentRuntime 持有独立的 ConversationManager 实例，直接维护单一会话的消息列表。
"""
from typing import List

from langchain_core.messages import BaseMessage


class ConversationManager:
    """对话上下文管理器 - 管理多轮对话历史"""

    def __init__(self, max_history: int = 20):
        self._messages: List[BaseMessage] = []

    def get_messages(self) -> List[BaseMessage]:
        """获取当前会话的消息列表（内部引用）"""
        return self._messages

    def add_message(self, message: BaseMessage) -> None:
        """添加消息到对话历史"""
        self.add_messages([message])

    def add_messages(self, messages: List[BaseMessage]) -> None:
        """批量添加消息到对话历史"""
        self._messages.extend(messages)

    def clear(self) -> None:
        """清空对话"""
        self._messages.clear()

    def get_history(self) -> List[BaseMessage]:
        """获取对话历史副本"""
        return list(self._messages)

    def set_history(self, history: List[BaseMessage]) -> None:
        """设置对话历史（预留持久化恢复使用）"""
        self._messages = history
