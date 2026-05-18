"""
Agent 异常定义
"""


class AgentError(Exception):
    """Agent 基础异常"""
    pass


class ValidationError(AgentError):
    """验证错误"""
    pass


class APIError(AgentError):
    """API 调用错误"""
    def __init__(self, message: str, status_code: int = None, response: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ParseError(AgentError):
    """解析错误"""
    pass


class MaxAttemptsError(AgentError):
    """达到最大尝试次数"""
    pass
