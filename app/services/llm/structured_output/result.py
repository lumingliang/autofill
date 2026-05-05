"""
结构化输出结果类
"""
from typing import Any, Dict


class StructuredOutputResult:
    """结构化输出结果"""
    def __init__(
        self,
        success: bool,
        data: Dict[str, Any] = None,
        method: str = "",
        error: str = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0
    ):
        self.success = success
        self.data = data or {}
        self.method = method
        self.error = error
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.latency_ms = 0
