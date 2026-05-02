"""
Agent 统一公开接口 (API Key 认证)

提供通用的 Agent 服务，支持通过自然语言执行各种操作。
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.autofill_auth import APIKeyAuth
from app.log import getLogger
from app.services.agent import AgentInput, AgentContext, QueryAgent

logger = getLogger(__name__)

agents_router = APIRouter()


class AgentRunRequest(BaseModel):
    """Agent 执行请求"""
    query: str = Field(..., description="用户查询语句，描述要执行的操作")
    curl: str = Field(..., description="API 调用的 curl 命令（无需占位符）")
    system_prompt: str = Field("", description="系统提示词，指导如何提取参数")
    expected_result: str = Field("", description="期望结果描述，用于验证")
    max_attempts: int = Field(5, description="最大尝试次数")
    timeout: int = Field(30, description="每次请求的超时时间(秒)")
    llm_model: str = Field("gpt-4o-mini", description="使用的 LLM 模型")
    llm_temperature: float = Field(0.0, description="温度参数")


class AgentRunResponse(BaseModel):
    """Agent 执行响应"""
    success: bool = Field(..., description="是否成功")
    status: str = Field(..., description="执行状态")
    data: Optional[Any] = Field(None, description="返回数据")
    error: Optional[str] = Field(None, description="错误信息")
    total_attempts: int = Field(0, description="尝试次数")
    execution_time_ms: int = Field(0, description="执行时间(毫秒)")


@agents_router.post("/v1/agent/run", summary="Agent 通用执行接口")
async def agent_run(
    request: AgentRunRequest,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
) -> AgentRunResponse:
    """
    Agent 通用执行接口

    通过自然语言执行 API 调用，自动提取参数并验证结果。
    支持多次尝试优化参数，直到获得满意结果。

    特点：
    - 无需 curl 占位符，直接传入完整 curl
    - 自动从 curl 中解析参数结构
    - 使用 LLM 从 query 中提取参数值
    - 自动验证结果是否符合预期

    请求参数:
    - query: 用户查询语句（如："查询上海体验中心店"）
    - curl: 完整的 curl 命令
    - system_prompt: 系统提示词（可选）
    - expected_result: 期望结果描述（可选）
    - max_attempts: 最大尝试次数（可选，默认5）
    - timeout: 超时时间（可选，默认30秒）
    - llm_model: 模型名称（可选，默认gpt-4o-mini）
    - llm_temperature: 温度参数（可选，默认0）

    示例请求:
    ```json
    {
        "query": "查询上海体验中心店",
        "curl": "curl -X POST 'http://api.example.com/search' -H 'Content-Type: application/json' -d '{\"name\": \"体验中心\", \"city\": \"上海\"}'",
        "system_prompt": "从查询中提取门店名称和城市",
        "expected_result": "返回上海地区的体验中心门店信息",
        "max_attempts": 3
    }
    ```
    """
    try:
        logger.info(f"[Agent API] 收到请求: {request.query}")

        # 构建上下文
        context = AgentContext(
            tenant_id=auth_info.get("tenant_id", 0),
            app_name=auth_info.get("app_name"),
            user_id=auth_info.get("user_id"),
            session_id=auth_info.get("session_id")
        )

        # 构建输入
        agent_input = AgentInput(
            query=request.query,
            curl=request.curl,
            system_prompt=request.system_prompt,
            expected_result=request.expected_result,
            max_attempts=request.max_attempts,
            timeout=request.timeout,
            llm_model=request.llm_model,
            llm_temperature=request.llm_temperature,
            context=context
        )

        # 创建 Agent 并执行
        agent = QueryAgent(context=context)
        result = await agent.run(agent_input)

        logger.info(f"[Agent API] 执行完成: success={result.success}, attempts={result.total_attempts}")

        return AgentRunResponse(
            success=result.success,
            status=result.status.value,
            data=result.data,
            error=result.error,
            total_attempts=result.total_attempts,
            execution_time_ms=result.execution_time_ms
        )

    except Exception as e:
        logger.error(f"[Agent API] 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return AgentRunResponse(
            success=False,
            status="failed",
            error=str(e),
            total_attempts=0,
            execution_time_ms=0
        )


@agents_router.post("/v1/agent/query", summary="Agent 查询接口（QueryAgent 别名）")
async def agent_query(
    request: AgentRunRequest,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
) -> AgentRunResponse:
    """
    Agent 查询接口

    与 /v1/agent/run 相同，提供更语义化的端点名称。
    """
    return await agent_run(request, auth_info)
