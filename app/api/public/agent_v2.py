"""
DataQueryAgent V2 公开接口 (API Key 认证)

基于 OpenAPI 规范的通用数据查询 Agent，支持自动工具生成和多轮交互决策。
"""
import traceback
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.autofill_auth import APIKeyAuth
from app.log import logger
from app.schemas.public import DataQueryRequest
from app.services.agent_v2 import DataQueryAgent, QueryResult

agent_v2_router = APIRouter()


class IterationRecordResponse(BaseModel):
    """迭代记录响应"""
    round: int = Field(..., description="迭代轮次")
    query: str = Field(..., description="查询内容")
    tool_name: Optional[str] = Field(None, description="调用的工具名称")
    tool_params: Dict[str, Any] = Field(default_factory=dict, description="工具参数")
    api_response: Any = Field(None, description="API 响应")
    agent_decision: str = Field(..., description="Agent 决策")
    reasoning: str = Field(..., description="决策理由")


class DataQueryResponse(BaseModel):
    """数据查询响应"""
    success: bool = Field(..., description="是否成功")
    agent_decision: str = Field(..., description="Agent 决策结果: complete/continue/need_more_info")
    api_response: Optional[Any] = Field(None, description="原始 API 响应数据")
    formatted_result: Optional[str] = Field(None, description="格式化后的查询结果")
    reasoning: str = Field(..., description="决策理由")
    iterations: List[IterationRecordResponse] = Field(default_factory=list, description="迭代记录")
    execution_time_ms: int = Field(0, description="执行时间(毫秒)")
    total_tokens: int = Field(0, description="总 Token 数")


class ToolInfoResponse(BaseModel):
    """工具信息响应"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")


class AvailableToolsResponse(BaseModel):
    """可用工具列表响应"""
    tools: List[ToolInfoResponse] = Field(default_factory=list, description="可用工具列表")
    total: int = Field(0, description="工具总数")


@agent_v2_router.post("/v2/agent/query", summary="DataQueryAgent V2 查询接口")
async def data_query_v2(
    request: DataQueryRequest,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
) -> DataQueryResponse:
    """
    DataQueryAgent V2 查询接口

    基于 OpenAPI 规范的通用数据查询 Agent，自动根据规范生成工具，
    使用多轮交互决策机制，直到获得满足用户需求的结果。

    特点：
    - 自动解析 OpenAPI 规范生成工具
    - 支持多轮交互决策
    - Agent 自主判断是否满足用户需求
    - 返回原始 API 响应和格式化结果

    请求参数:
    - query: 用户查询语句（如："查询北京比亚迪门店"）
    - openapi_spec: OpenAPI 规范来源（URL 或本地文件路径）
    - api_key: API 认证密钥（可选）
    - headers: 自定义请求头（可选）
    - max_iterations: 最大迭代次数（可选，默认5）
    - temperature: LLM 温度参数（可选，默认0）
    - chat_history: 聊天记录（可选）

    示例请求:
    ```json
    {
        "query": "查询北京比亚迪门店",
        "openapi_spec": "https://api.example.com/openapi.json",
        "max_iterations": 5
    }
    ```

    响应说明:
    - agent_decision: complete(完成)/continue(继续)/need_more_info(需要更多信息)
    - api_response: 原始 API 响应数据（JSON）
    - formatted_result: 格式化后的查询结果（自然语言）
    - iterations: 每轮迭代的详细记录
    """
    try:
        logger.info(f"[AgentV2 API] 收到查询请求: {request.query}")

        # 创建 Agent
        agent = DataQueryAgent(
            openapi_spec=request.openapi_spec,
            api_key=request.api_key,
            headers=request.headers or {},
            max_iterations=request.max_iterations,
            tenant_id=auth_info.get("tenant_id", 0),
            app_name=auth_info.get("app_name"),
            temperature=request.temperature,
        )

        # 执行查询
        result = await agent.query(
            user_query=request.query,
            chat_history=request.chat_history
        )

        logger.info(f"[AgentV2 API] 查询完成: decision={result.agent_decision}")

        # 转换迭代记录
        iterations = [
            IterationRecordResponse(
                round=it.round,
                query=it.query,
                tool_name=it.tool_name,
                tool_params=it.tool_params,
                api_response=it.api_response,
                agent_decision=it.agent_decision,
                reasoning=it.reasoning,
            )
            for it in result.iterations
        ]

        return DataQueryResponse(
            success=result.agent_decision == "complete",
            agent_decision=result.agent_decision,
            api_response=result.api_response,
            formatted_result=result.formatted_result,
            reasoning=result.reasoning,
            iterations=iterations,
            execution_time_ms=result.execution_time_ms,
            total_tokens=result.total_tokens,
        )

    except Exception as e:
        logger.error(f"[AgentV2 API] 查询失败: {e}")
        traceback.print_exc()
        return DataQueryResponse(
            success=False,
            agent_decision="failed",
            api_response=None,
            formatted_result=None,
            reasoning=f"执行失败: {str(e)}",
            iterations=[],
            execution_time_ms=0,
            total_tokens=0,
        )


@agent_v2_router.post("/v2/agent/tools", summary="获取可用工具列表")
async def get_available_tools(
    request: DataQueryRequest,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
) -> AvailableToolsResponse:
    """
    获取 DataQueryAgent V2 的可用工具列表

    根据 OpenAPI 规范返回所有可用的工具信息。

    请求参数:
    - openapi_spec: OpenAPI 规范来源（URL 或本地文件路径）
    - api_key: API 认证密钥（可选）
    - headers: 自定义请求头（可选）
    """
    try:
        logger.info(f"[AgentV2 API] 获取工具列表: {request.openapi_spec}")

        # 创建 Agent
        agent = DataQueryAgent(
            openapi_spec=request.openapi_spec,
            api_key=request.api_key,
            headers=request.headers or {},
            tenant_id=auth_info.get("tenant_id", 0),
            app_name=auth_info.get("app_name"),
        )

        # 获取工具列表
        tool_names = agent.get_available_tools()

        tools = []
        for name in tool_names:
            details = agent.get_tool_details(name)
            if details:
                tools.append(ToolInfoResponse(
                    name=details["name"],
                    description=details["description"][:200] + "..." if len(details["description"]) > 200 else details["description"]
                ))

        return AvailableToolsResponse(
            tools=tools,
            total=len(tools)
        )

    except Exception as e:
        logger.error(f"[AgentV2 API] 获取工具列表失败: {e}")
        traceback.print_exc()
        return AvailableToolsResponse(
            tools=[],
            total=0
        )


@agent_v2_router.post("/v2/agent/query/simple", summary="简化版查询接口（无需认证）")
async def data_query_v2_simple(
    request: DataQueryRequest
) -> DataQueryResponse:
    """
    DataQueryAgent V2 简化版查询接口

    与 /v2/agent/query 功能相同，但不需要 API Key 认证。
    适用于内部调用或测试场景。
    """
    auth_info = {
        "tenant_id": 0,
        "app_name": None,
        "user_id": None,
        "session_id": None,
    }
    return await data_query_v2(request, auth_info)
