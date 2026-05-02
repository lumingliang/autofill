"""
Agent 基础类型定义
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class AgentStatus(str, Enum):
    """Agent 执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    MAX_ATTEMPTS_REACHED = "max_attempts_reached"


@dataclass
class AgentContext:
    """Agent 上下文"""
    tenant_id: int = 0
    app_name: Optional[str] = None
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentInput:
    """Agent 输入"""
    query: str
    curl: str
    system_prompt: str = ""
    expected_result: str = ""
    max_attempts: int = 5
    timeout: int = 30
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0
    context: AgentContext = field(default_factory=AgentContext)


@dataclass
class APIResult:
    """API 调用结果"""
    success: bool
    status_code: int
    data: Any = None
    error: Optional[str] = None
    raw_response: Optional[str] = None


@dataclass
class AttemptRecord:
    """尝试记录"""
    attempt_number: int
    params: Dict[str, Any]
    api_result: APIResult
    is_valid: bool
    reason: str = ""


@dataclass
class AgentOutput:
    """Agent 输出"""
    success: bool
    status: AgentStatus
    data: Any = None
    error: Optional[str] = None
    attempts: List[AttemptRecord] = field(default_factory=list)
    total_attempts: int = 0
    execution_time_ms: int = 0
