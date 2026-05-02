"""
Query Agent 模块

通用查询 Agent，支持通过 curl 模板智能查询数据。
"""

from .agent import QueryAgent
from .types import (
    QueryAgentInput,
    QueryAgentOutput,
    SearchAttempt,
    ParsedCurl,
    QueryAgentError,
    CurlParseError,
    SearchTimeoutError,
    LLMResponseError
)
from .parser import CurlParser, parse_curl
from .utils import (
    replace_placeholders,
    replace_placeholders_in_curl,
    extract_by_selector
)

__all__ = [
    "QueryAgent",
    "QueryAgentInput",
    "QueryAgentOutput",
    "SearchAttempt",
    "ParsedCurl",
    "QueryAgentError",
    "CurlParseError",
    "SearchTimeoutError",
    "LLMResponseError",
    "CurlParser",
    "parse_curl",
    "replace_placeholders",
    "replace_placeholders_in_curl",
    "extract_by_selector"
]
