"""
会话历史管理器
"""
from typing import Dict

from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory


class SessionHistoryManager:
    """
    会话历史管理器 - 使用LangChain原生InMemoryChatMessageHistory
    支持滑动窗口记忆（通过max_rounds限制消息数量）
    """

    def __init__(self, max_rounds: int = 10):
        self.max_rounds = max_rounds
        self._histories: Dict[str, InMemoryChatMessageHistory] = {}

    def get_history(self, session_id: str) -> InMemoryChatMessageHistory:
        """获取或创建指定session的聊天历史"""
        if session_id not in self._histories:
            self._histories[session_id] = InMemoryChatMessageHistory()
        return self._histories[session_id]

    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """供RunnableWithMessageHistory使用的回调函数"""
        return self.get_history(session_id)

    def clear_session(self, session_id: str):
        """清除指定session的历史"""
        if session_id in self._histories:
            del self._histories[session_id]

    def trim_history(self, session_id: str, max_rounds: int = None):
        """
        修剪历史消息，保留最近N轮对话
        每轮对话包含一条HumanMessage和一条AIMessage
        max_rounds=0 表示清空所有历史消息
        """
        if session_id not in self._histories:
            return

        history = self._histories[session_id]
        max_rounds = self.max_rounds if max_rounds is None else max_rounds
        max_messages = max_rounds * 2  # 每轮2条消息

        messages = history.messages
        if len(messages) > max_messages:
            # 保留最近的消息
            history.messages = messages[-max_messages:]
