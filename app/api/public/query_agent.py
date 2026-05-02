"""
QueryAgent 公开接口 (API Key 认证)

提供通用查询 Agent 服务，支持通过自然语言查询外部 API
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.core.autofill_auth import APIKeyAuth
from app.log import getLogger
from app.services.query_agent.agent import QueryAgent
from app.services.query_agent.types import QueryAgentInput, QueryAgentOutput

logger = getLogger(__name__)

query_agent_public_router = APIRouter()


class QueryAgentRequest(BaseModel):
    """QueryAgent 请求模型"""
    query: str = Field(..., description="用户查询语句")
    curl: str = Field(..., description="curl 请求模板，使用 {{placeholder}} 作为占位符")
    system_prompt: str = Field(..., description="系统提示词，指导 LLM 如何提取参数")
    max_attempts: int = Field(5, description="最大尝试次数")
    timeout: int = Field(30, description="每次请求的超时时间(秒)")
    llm_model: str = Field("C4AI-Command-R-Plus", description="使用的 LLM 模型")
    llm_temperature: float = Field(0.0, description="温度参数")
    return_raw_response: bool = Field(False, description="是否返回原始响应")
    result_selector: Optional[str] = Field(None, description="结果选择器，如: data.0 或 $.data[0]")


@query_agent_public_router.post("/v1/query_agent/run", summary="QueryAgent 通用查询接口")
async def query_agent_run(
    request: QueryAgentRequest,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
) -> QueryAgentOutput:
    """
    QueryAgent 通用查询接口

    通过自然语言查询外部 API，自动提取参数并执行查询。
    支持多次尝试优化参数，直到获得满意结果。

    请求参数:
    - query: 用户查询语句
    - curl: curl 请求模板，使用 {{placeholder}} 作为占位符
    - system_prompt: 系统提示词
    - max_attempts: 最大尝试次数（可选，默认5）
    - timeout: 超时时间（可选，默认30秒）
    - llm_model: 模型名称（可选，默认C4AI-Command-R-Plus）
    - llm_temperature: 温度参数（可选，默认0）
    - return_raw_response: 是否返回原始响应（可选，默认false）
    - result_selector: 结果选择器（可选，如："data.0" 或 "$.data[0]"）

    示例请求:
    ```json
    {
        "query": "查询上海体验中心店",
        "curl": "curl -X POST 'http://api.example.com/search' -H 'Content-Type: application/json' -d '{\"name\": \"{{name}}\", \"city\": \"{{city}}\"}'",
        "system_prompt": "从查询中提取门店名称和城市",
        "max_attempts": 3,
        "timeout": 30
    }
    ```
    """
    try:
        agent = QueryAgent()

        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(
                pool,
                agent.run_with_input,
                QueryAgentInput(
                    query=request.query,
                    curl=request.curl,
                    system_prompt=request.system_prompt,
                    max_attempts=request.max_attempts,
                    timeout=request.timeout,
                    llm_model=request.llm_model,
                    llm_temperature=request.llm_temperature,
                    return_raw_response=request.return_raw_response,
                    result_selector=request.result_selector
                )
            )

        return result

    except Exception as e:
        logger.error(f"[QueryAgent] 查询失败: {e}")
        import traceback
        traceback.print_exc()
        return QueryAgentOutput(
            success=False,
            data=None,
            attempts=0,
            reasoning=f"查询执行失败: {str(e)}",
            is_satisfied=False
        )
