"""
Query Agent - 智能查询 Agent

使用 Function Calling 实现多轮交互：
- call_api: 发起 API 请求
- validate_result: 验证结果并决定是否继续

流程：
1. 第一轮：LLM 输出 call_api 参数
2. 第二轮：将 API 结果返回给 LLM
3. 第三轮：LLM 使用 validate_result 判断是否需要继续调整
"""
import time
import uuid
import json
from typing import Any, Dict, List, Optional

from app.log import logger

from ..base.agent import BaseAgent
from ..base.types import AgentInput, AgentOutput, AgentStatus, AttemptRecord, APIResult, AgentContext
from ..base.exceptions import AgentError
from ..core.curl_parser import CurlParser, ParsedCurl, ParamSchema
from ..core.api_executor import APIExecutor
from ..core.result_validator import ResultValidator


class QueryAgent(BaseAgent):
    """
    查询 Agent

    通过自然语言查询外部 API，使用多轮 Function Calling 自动提取参数、
    执行查询并验证结果，直到获得满意结果。
    """

    def __init__(self, context: Optional[AgentContext] = None):
        super().__init__(name="query_agent")
        self.context = context or AgentContext()

        # 初始化组件
        self.curl_parser = CurlParser()
        self.api_executor = APIExecutor()
        self.result_validator = ResultValidator(
            tenant_id=self.context.tenant_id,
            app_name=self.context.app_name
        )

    async def run(self, input_data: AgentInput) -> AgentOutput:
        """
        执行查询

        Args:
            input_data: Agent 输入

        Returns:
            AgentOutput: 查询结果
        """
        logger.info(f"[QueryAgent] 开始执行查询: {input_data.query}")
        start_time = time.time()

        try:
            # 1. 解析 curl
            parsed = self.curl_parser.parse(input_data.curl)
            logger.info(f"[QueryAgent] 解析 curl 完成: {parsed.method} {parsed.url}")

            # 2. 检查是否有参数需要提取
            if not parsed.param_schemas:
                result = await self._execute_without_params(parsed)
                execution_time = int((time.time() - start_time) * 1000)
                return AgentOutput(
                    success=result.success,
                    status=AgentStatus.SUCCESS if result.success else AgentStatus.FAILED,
                    data=result.data,
                    error=result.error,
                    total_attempts=1,
                    execution_time_ms=execution_time
                )

            # 3. 使用多轮对话执行查询
            return await self._execute_with_conversation(input_data, parsed)

        except Exception as e:
            logger.error(f"[QueryAgent] 执行失败: {e}")
            execution_time = int((time.time() - start_time) * 1000)
            return AgentOutput(
                success=False,
                status=AgentStatus.FAILED,
                error=str(e),
                total_attempts=0,
                execution_time_ms=execution_time
            )

    async def _execute_without_params(self, parsed: ParsedCurl) -> APIResult:
        """无需参数，直接执行"""
        return await self.api_executor.execute(parsed, {})

    async def _execute_with_conversation(
        self,
        input_data: AgentInput,
        parsed: ParsedCurl
    ) -> AgentOutput:
        """
        使用多轮对话执行查询

        每轮对话：
        1. LLM 决定调用 call_api（输出参数）或 finish（结束）
        2. 如果是 call_api，执行 API 并将结果返回给 LLM
        3. LLM 验证结果，决定继续调整参数或结束
        """
        from app.services.llm.llm_config_utils import get_default_llm_config
        from app.services.llm.llm_proxy_service import llm_proxy_service

        start_time = time.time()
        attempts = []
        session_id = str(uuid.uuid4())

        # 获取 LLM 配置
        config = await get_default_llm_config(
            tenant_id=self.context.tenant_id,
            app_name=self.context.app_name
        )

        if not config:
            raise AgentError("未找到 LLM 配置")

        # 构建 tools
        tools = self._build_tools(parsed.param_schemas)

        # 初始查询
        current_query = input_data.query
        if input_data.expected_result:
            current_query = f"{current_query}\n\n预期结果: {input_data.expected_result}"

        for attempt in range(input_data.max_attempts):
            logger.info(f"[QueryAgent] 第 {attempt + 1} 次尝试")

            try:
                # 调用 LLM，让 LLM 决定下一步
                # 使用 custom_fc_non_stream 方法支持多 tool 选择
                result = await llm_proxy_service.process_request(
                    query=current_query,
                    tools=tools,
                    system_prompt=input_data.system_prompt or self._build_system_prompt(parsed),
                    tool_choice="auto",
                    method="bind_tools_stream",
                    config=config,
                    session_id=session_id,
                    memory_rounds=input_data.max_attempts * 3
                )

                # 解析 LLM 的决策
                action = result.get("action")
                params = result.get("params", {})
                reason = result.get("reason", "")

                if action == "finish":
                    # LLM 决定结束，返回结果
                    execution_time = int((time.time() - start_time) * 1000)
                    logger.info(f"[QueryAgent] LLM 决定结束查询: {reason}")

                    last_attempt = attempts[-1] if attempts else None
                    return AgentOutput(
                        success=True,
                        status=AgentStatus.SUCCESS,
                        data=last_attempt.api_result.data if last_attempt else {},
                        attempts=attempts,
                        total_attempts=attempt + 1,
                        execution_time_ms=execution_time
                    )

                elif action == "call_api":
                    # LLM 决定调用 API
                    logger.info(f"[QueryAgent] LLM 决定调用 API: {params}")

                    # 执行 API
                    api_result = await self.api_executor.execute(parsed, params)

                    # 记录尝试
                    record = AttemptRecord(
                        attempt_number=attempt + 1,
                        params=params.copy(),
                        api_result=api_result,
                        is_valid=False,  # 待验证
                        reason=""
                    )
                    attempts.append(record)

                    # 将 API 结果返回给 LLM，让它决定下一步
                    current_query = self._build_result_feedback(api_result)

                else:
                    # 未知的 action，尝试结束
                    logger.warning(f"[QueryAgent] 未知的 action: {action}")
                    break

            except Exception as e:
                logger.exception(f"[QueryAgent] 第 {attempt + 1} 次尝试失败: {e}")
                record = AttemptRecord(
                    attempt_number=attempt + 1,
                    params={},
                    api_result=APIResult(success=False, status_code=0, error=str(e)),
                    is_valid=False,
                    reason=str(e)
                )
                attempts.append(record)

        # 达到最大尝试次数
        execution_time = int((time.time() - start_time) * 1000)
        logger.warning(f"[QueryAgent] 达到最大尝试次数: {input_data.max_attempts}")

        last_attempt = attempts[-1] if attempts else None
        return AgentOutput(
            success=False,
            status=AgentStatus.MAX_ATTEMPTS_REACHED,
            data=last_attempt.api_result.data if last_attempt else None,
            error="达到最大尝试次数，未能获得满意结果",
            attempts=attempts,
            total_attempts=len(attempts),
            execution_time_ms=execution_time
        )

    def _build_tools(self, param_schemas: List[ParamSchema]) -> List[Dict[str, Any]]:
        """构建 Function Calling tools"""
        # 构建 call_api 的参数 schema
        properties = {}
        required = []

        for schema in param_schemas:
            properties[schema.name] = {
                "type": schema.param_type,
                "description": schema.description
            }
            if schema.required:
                required.append(schema.name)

        return [
            {
                "type": "function",
                "function": {
                    "name": "call_api",
                    "description": "调用 API 查询数据",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            **properties,
                            "reason": {
                                "type": "string",
                                "description": "选择这些参数的原因"
                            }
                        },
                        "required": required + ["reason"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "finish",
                    "description": "结束查询，返回最终结果",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": "结束查询的原因"
                            }
                        },
                        "required": ["reason"]
                    }
                }
            }
        ]

    def _build_system_prompt(self, parsed: ParsedCurl) -> str:
        """构建系统提示词"""
        return f"""你是一个智能信息提取助手。你的任务是分析用户提供的上下文（可能是查询语句、聊天记录或其他文本），从中提取关键信息，然后调用 API 获取相关数据。

API 信息:
- 方法: {parsed.method}
- URL: {parsed.url}

你的工作流程:
1. 仔细分析用户提供的上下文，理解用户真正需要查询什么
2. 从上下文中提取合适的参数值
3. 使用 call_api 工具调用 API
4. 查看 API 返回结果
5. 如果结果满足需求，使用 finish 工具结束
6. 如果结果不满足，调整参数再次调用 call_api

注意事项:
- 用户输入可能是直接查询，也可能是聊天记录，需要你从中提取查询意图
- 如果关键词太具体（如"海洋网系列"），尝试更通用的词（如"海洋网"）
- 如果某个参数限制太严格，考虑放宽或移除
- 如果组合条件太苛刻，尝试减少条件
- 检查是否有拼写错误或同义词问题"""

    def _build_result_feedback(self, api_result: APIResult, max_length: int = 8000) -> str:
        """构建 API 结果反馈
        
        Args:
            api_result: API 调用结果
            max_length: 最大内容长度，超出将截断
        """
        # 处理响应内容，确保是字符串格式
        if api_result.raw_response:
            response_content = api_result.raw_response
        elif api_result.data:
            try:
                import json
                response_content = json.dumps(api_result.data, ensure_ascii=False, indent=2)
            except:
                response_content = str(api_result.data)
        else:
            response_content = "无响应数据"

        # 截断过长的内容
        if len(response_content) > max_length:
            truncated_length = len(response_content) - max_length
            response_content = response_content[:max_length] + f"\n... (已截断 {truncated_length} 字符)"

        return f"""API 调用结果：

```
{response_content}
```

请分析这个结果是否满足用户的需求。
- 如果满足，请使用 finish 工具结束
- 如果不满足，请分析原因并使用 call_api 工具调整参数重新查询"""
