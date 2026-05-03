"""
Query Agent - 重构后的简化版本

使用新的 Agent 架构：
- CurlParser: 无需占位符解析 curl
- ParamExtractor: 复用 llm_proxy 提取参数
- APIExecutor: 执行 API 调用
- ResultValidator: 验证结果
"""
import time
from typing import Any, Dict, List, Optional

from app.log import logger

from ..base.agent import BaseAgent
from ..base.types import AgentInput, AgentOutput, AgentStatus, AttemptRecord, APIResult, AgentContext
from ..base.exceptions import AgentError
from ..core.curl_parser import CurlParser, ParsedCurl
from ..core.param_extractor import ParamExtractor
from ..core.api_executor import APIExecutor
from ..core.result_validator import ResultValidator


class QueryAgent(BaseAgent):
    """
    查询 Agent

    通过自然语言查询外部 API，自动提取参数并执行查询。
    支持多次尝试优化参数，直到获得满意结果。

    特点：
    - 无需 curl 占位符，直接解析完整 curl
    - 复用 llm_proxy 的 FC 能力提取参数
    - 简化的架构，易于维护和扩展
    """

    def __init__(self, context: Optional[AgentContext] = None):
        super().__init__(name="query_agent")
        self.context = context or AgentContext()

        # 初始化组件
        self.curl_parser = CurlParser()
        self.param_extractor = ParamExtractor(
            tenant_id=self.context.tenant_id,
            app_name=self.context.app_name
        )
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
                # 没有参数，直接执行
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

            # 3. 带重试的执行
            return await self._execute_with_retry(input_data, parsed)

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

    async def _execute_with_retry(
        self,
        input_data: AgentInput,
        parsed: ParsedCurl
    ) -> AgentOutput:
        """带重试的执行"""
        start_time = time.time()
        attempts = []
        current_params = {}

        for attempt in range(input_data.max_attempts):
            logger.info(f"[QueryAgent] 第 {attempt + 1} 次尝试")

            try:
                # 提取/优化参数
                if attempt == 0:
                    current_params = await self.param_extractor.extract(
                        query=input_data.query,
                        param_schemas=parsed.param_schemas,
                        system_prompt=input_data.system_prompt,
                        llm_model=input_data.llm_model,
                        llm_temperature=input_data.llm_temperature
                    )
                else:
                    # 重试策略：让大模型根据历史记录反省并优化参数
                    last_params = attempts[-1].params if attempts else {}
                    last_result = attempts[-1].api_result if attempts else None
                    last_reason = attempts[-1].reason if attempts else ""
                    
                    # 构建历史记录上下文
                    history_context = self._build_retry_context(attempts)
                    
                    # 构建反馈信息
                    feedback = f"""
前一次查询未能获得满意结果。

历史尝试记录:
{history_context}

请分析为什么之前的查询没有返回结果，并调整参数。
可能的优化方向：
1. 如果关键词太具体（如"海洋网系列"），尝试更通用的词（如"海洋网"）
2. 如果某个参数限制太严格，考虑放宽或移除
3. 如果组合条件太苛刻，尝试减少条件
4. 检查是否有拼写错误或同义词问题

请给出新的参数组合。"""
                    
                    current_params = await self.param_extractor.refine(
                        query=input_data.query,
                        param_schemas=parsed.param_schemas,
                        previous_params=last_params,
                        previous_result=last_result.raw_response if last_result else "",
                        feedback=feedback,
                        llm_model=input_data.llm_model,
                        llm_temperature=input_data.llm_temperature
                    )

                logger.info(f"[QueryAgent] 提取参数: {current_params}")

                # 执行 API
                api_result = await self.api_executor.execute(parsed, current_params)

                # 验证结果
                is_valid, reason = await self.result_validator.validate(
                    api_result=api_result,
                    query=input_data.query,
                    expected_result=input_data.expected_result,
                    llm_model=input_data.llm_model,
                    llm_temperature=input_data.llm_temperature
                )

                # 记录尝试
                record = AttemptRecord(
                    attempt_number=attempt + 1,
                    params=current_params.copy(),
                    api_result=api_result,
                    is_valid=is_valid,
                    reason=reason
                )
                attempts.append(record)

                # 检查是否成功
                if api_result.success and is_valid:
                    execution_time = int((time.time() - start_time) * 1000)
                    logger.info(f"[QueryAgent] 查询成功，共 {attempt + 1} 次尝试")
                    return AgentOutput(
                        success=True,
                        status=AgentStatus.SUCCESS,
                        data=api_result.data,
                        attempts=attempts,
                        total_attempts=attempt + 1,
                        execution_time_ms=execution_time
                    )

                logger.info(f"[QueryAgent] 结果不符合预期: {reason}")

            except Exception as e:
                logger.exception(f"[QueryAgent] 第 {attempt + 1} 次尝试失败: {e}")
                record = AttemptRecord(
                    attempt_number=attempt + 1,
                    params=current_params.copy(),
                    api_result=APIResult(success=False, status_code=0, error=str(e)),
                    is_valid=False,
                    reason=str(e)
                )
                attempts.append(record)

        # 达到最大尝试次数
        execution_time = int((time.time() - start_time) * 1000)
        logger.warning(f"[QueryAgent] 达到最大尝试次数: {input_data.max_attempts}")

        # 返回最后一次尝试的结果
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

    def _build_retry_context(self, attempts: List[AttemptRecord]) -> str:
        """
        构建重试上下文，让大模型了解历史尝试记录
        """
        if not attempts:
            return "无历史记录"
        
        context_lines = []
        for record in attempts:
            status = "✓ 成功" if record.is_valid else "✗ 失败"
            context_lines.append(f"""
尝试 #{record.attempt_number}:
- 参数: {record.params}
- 结果: {status}
- 原因: {record.reason}
- API返回: {record.api_result.raw_response[:200] if record.api_result else "N/A"}
""")
        
        return "\n".join(context_lines)
