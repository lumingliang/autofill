"""
Agent 基础抽象类
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import time

from app.log import logger

from .types import AgentInput, AgentOutput, AgentContext, AgentStatus, AttemptRecord
from .exceptions import AgentError, MaxAttemptsError


class BaseAgent(ABC):
    """Agent 基础抽象类"""

    def __init__(self, name: str = "base_agent"):
        self.name = name
        self.logger = logger.bind(agent_name=name)

    @abstractmethod
    async def run(self, input_data: AgentInput) -> AgentOutput:
        """
        执行 Agent

        Args:
            input_data: Agent 输入

        Returns:
            AgentOutput: 执行结果
        """
        pass

    async def execute_with_retry(
        self,
        input_data: AgentInput,
        execute_fn,
        validate_fn
    ) -> AgentOutput:
        """
        带重试的执行

        Args:
            input_data: 输入数据
            execute_fn: 执行函数
            validate_fn: 验证函数

        Returns:
            AgentOutput
        """
        start_time = time.time()
        attempts = []

        for attempt in range(input_data.max_attempts):
            self.logger.info(f"[{self.name}] 第 {attempt + 1} 次尝试")

            try:
                # 执行
                result = await execute_fn(attempt, attempts)

                # 验证
                is_valid, reason = await validate_fn(result, input_data.query)

                record = AttemptRecord(
                    attempt_number=attempt + 1,
                    params=result.get("params", {}),
                    api_result=result.get("api_result"),
                    is_valid=is_valid,
                    reason=reason
                )
                attempts.append(record)

                if is_valid:
                    execution_time = int((time.time() - start_time) * 1000)
                    return AgentOutput(
                        success=True,
                        status=AgentStatus.SUCCESS,
                        data=result.get("api_result").data,
                        attempts=attempts,
                        total_attempts=attempt + 1,
                        execution_time_ms=execution_time
                    )

                self.logger.info(f"[{self.name}] 结果不符合预期: {reason}")

            except Exception as e:
                self.logger.error(f"[{self.name}] 执行异常: {e}")
                record = AttemptRecord(
                    attempt_number=attempt + 1,
                    params={},
                    api_result=None,
                    is_valid=False,
                    reason=str(e)
                )
                attempts.append(record)

        # 达到最大尝试次数
        execution_time = int((time.time() - start_time) * 1000)
        return AgentOutput(
            success=False,
            status=AgentStatus.MAX_ATTEMPTS_REACHED,
            error="达到最大尝试次数，未能获得满意结果",
            attempts=attempts,
            total_attempts=len(attempts),
            execution_time_ms=execution_time
        )
