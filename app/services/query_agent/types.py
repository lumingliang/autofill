"""
Query Agent 类型定义
"""
from typing import Any, Dict, List, Optional, TypedDict
from dataclasses import dataclass
from pydantic import BaseModel


@dataclass
class ParsedCurl:
    """解析后的 Curl 命令"""
    url: str
    method: str
    headers: Dict[str, str]
    body_template: Optional[Dict]
    query_params_template: Optional[Dict]
    placeholder_fields: List[str]
    # 从 curl body 中提取的参数结构（用于构建 FC 调用的参数）
    param_schema: Optional[Dict] = None


class SearchAttempt(BaseModel):
    """单次搜索尝试记录"""
    attempt_number: int
    parameters: Dict[str, str]
    result_count: int
    selected_indices: List[int]
    reasoning: str
    raw_response: Optional[Dict] = None


class QueryAgentInput(BaseModel):
    """Agent 输入参数 - 支持调用方自定义关键参数"""
    query: str
    curl: str
    system_prompt: str

    # 可配置的关键参数（由调用方传入，不设置默认值）
    max_attempts: int = 5
    timeout: int = 30
    llm_model: str = "C4AI-Command-R-Plus"  # 默认使用 LiteLLM 配置的模型
    llm_temperature: float = 0.0
    return_raw_response: bool = False
    result_selector: Optional[str] = None


class QueryAgentOutput(BaseModel):
    """Agent 输出结果 - 保持与原接口数据结构一致"""
    success: bool
    data: Optional[Any] = None
    raw_response: Optional[Dict] = None
    attempts: int = 0
    history: List[SearchAttempt] = []
    reasoning: str = ""
    final_parameters: Dict[str, str] = {}
    is_satisfied: bool = False


class QueryAgentState(TypedDict, total=False):
    """LangGraph 状态定义"""
    # 输入参数
    query: str
    curl_template: str  # 原始 curl 模板，用于 curl-session
    parsed_curl: ParsedCurl
    system_prompt: str

    # 可配置参数
    max_attempts: int
    timeout: int
    llm_model: str
    llm_temperature: float
    return_raw_response: bool
    result_selector: Optional[str]

    # 执行状态
    current_parameters: Dict[str, str]
    current_results: Optional[Dict]
    search_history: List[SearchAttempt]
    attempt_count: int

    # 结果
    final_result: Optional[Any]
    final_raw_response: Optional[Dict]
    final_reasoning: str
    is_satisfied: bool

    # 工作流内部使用
    messages: List[Any]


class QueryAgentError(Exception):
    """Agent 基础异常"""
    pass


class CurlParseError(QueryAgentError):
    """Curl 解析异常"""
    pass


class SearchTimeoutError(QueryAgentError):
    """搜索超时异常"""
    pass


class LLMResponseError(QueryAgentError):
    """LLM 响应解析异常"""
    pass
