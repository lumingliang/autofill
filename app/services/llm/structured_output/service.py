"""
结构化输出服务主类
"""
import time
from datetime import datetime
from typing import List, Optional

from app.log import logger
from app.models.llm_config import LLMConfig
from app.services.llm.structured_output.history_manager import SessionHistoryManager
from app.services.llm.structured_output.methods import StructuredOutputMethods
from app.services.llm.structured_output.result import StructuredOutputResult
from app.settings.config import settings


class StructuredOutputService:
    """结构化输出服务 - 支持多轮对话记忆（LangChain原生实现）"""

    # 默认方法优先级
    DEFAULT_METHOD_PRIORITY = [
        "with_structured_output",
        "bind_tools_stream",
        "custom_fc_non_stream",
        "custom_fc_stream",
        "pydantic_parser",
        "json_parser"
    ]

    # 类级别的历史管理器（所有实例共享）
    _history_manager = SessionHistoryManager(max_rounds=10)

    def __init__(self, config: LLMConfig):
        self.config = config
        self.litellm_params = config.litellm_params or {}
        self.model_name = config.name
        self.api_key = self.litellm_params.get("api_key", "")
        self.api_base = self.litellm_params.get("api_base", None)
        self.timeout = self.litellm_params.get("timeout", 60)

        # 获取结构化输出配置
        self.structured_config = settings.STRUCTURED_OUTPUT_CONFIG
        self.failed_threshold = self.structured_config.get("failed_threshold", 2)
        self.enable_fallback = self.structured_config.get("enable_fallback", True)
        self.max_attempt_methods = self.structured_config.get("max_attempt_methods", 6)

        # 初始化方法执行器
        litellm_config = settings.LITELLM_CONFIG
        base_url = litellm_config.get("base_url", "http://localhost:4000")
        master_key = litellm_config.get("master_key", "")

        self.methods = StructuredOutputMethods(
            model_name=self.model_name,
            api_key=master_key,
            base_url=f"{base_url}/v1",
            timeout=self.timeout
        )

    @classmethod
    def get_history_manager(cls) -> SessionHistoryManager:
        """获取历史管理器"""
        return cls._history_manager

    @classmethod
    def clear_session(cls, session_id: str):
        """清除指定session的历史"""
        cls._history_manager.clear_session(session_id)

    def _get_supported_methods(self) -> List[str]:
        """获取支持的方法列表（根据 capabilities）"""
        capabilities = self.config.capabilities or {}
        structured_methods = capabilities.get("structured_output_methods", {})

        supported = []
        for method in self.DEFAULT_METHOD_PRIORITY:
            method_config = structured_methods.get(method, {})
            if method_config.get("supported", True):
                supported.append(method)

        return supported

    async def generate(
        self,
        query: str,
        tools: List[dict],
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto",
        method: str = None
    ) -> StructuredOutputResult:
        """
        生成结构化输出，支持多轮对话记忆
        """
        start_time = time.time()

        # 如果指定了方法，直接使用
        if method:
            try:
                result = await self._try_method(
                    method=method,
                    query=query,
                    tools=tools,
                    system_prompt=system_prompt,
                    session_id=session_id,
                    memory_rounds=memory_rounds,
                    tool_choice=tool_choice
                )
                if result.success:
                    result.latency_ms = int((time.time() - start_time) * 1000)
                return result
            except Exception as e:
                return StructuredOutputResult(
                    success=False,
                    error=f"{type(e).__name__}: {e}",
                    method=method
                )

        # 确定方法优先级
        methods_to_try = self._get_supported_methods()
        methods_to_try = methods_to_try[:self.max_attempt_methods]

        last_error = None
        result = None

        for method_name in methods_to_try:
            try:
                result = await self._try_method(
                    method=method_name,
                    query=query,
                    tools=tools,
                    system_prompt=system_prompt,
                    session_id=session_id,
                    memory_rounds=memory_rounds,
                    tool_choice=tool_choice
                )

                if result.success:
                    result.latency_ms = int((time.time() - start_time) * 1000)
                    break
                else:
                    last_error = result.error
                    await self._record_method_failure(method_name, result.error)

            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                logger.error(f"Method {method_name} failed: {type(e).__name__}: {e}")
                await self._record_method_failure(method_name, f"{type(e).__name__}: {e}")

        if result and result.success:
            return result

        # 所有方法都失败
        return StructuredOutputResult(
            success=False,
            error=f"所有方法都失败，最后错误: {last_error}",
            method="none"
        )

    async def _try_method(
        self,
        method: str,
        query: str,
        tools: List[dict],
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto"
    ) -> StructuredOutputResult:
        """尝试使用指定方法"""
        method_map = {
            "with_structured_output": self.methods.method_with_structured_output,
            "bind_tools_non_stream": self.methods.method_bind_tools_non_stream,
            "bind_tools_stream": self.methods.method_bind_tools_stream,
            "custom_fc_non_stream": self.methods.method_custom_fc_non_stream,
            "custom_fc_stream": self.methods.method_custom_fc_stream,
            "pydantic_parser": self.methods.method_pydantic_parser,
            "json_parser": self.methods.method_json_parser,
        }

        if method not in method_map:
            return StructuredOutputResult(
                success=False,
                error=f"未知方法: {method}",
                method=method
            )

        return await method_map[method](
            query=query,
            tools=tools,
            system_prompt=system_prompt,
            session_id=session_id,
            memory_rounds=memory_rounds,
            tool_choice=tool_choice,
            history_manager=self._history_manager
        )

    async def _record_method_failure(self, method: str, error: str):
        """记录方法失败"""
        capabilities = self.config.capabilities or LLMConfig.get_default_capabilities()
        structured_methods = capabilities.get("structured_output_methods", {})

        if method in structured_methods:
            method_config = structured_methods[method]
            method_config["failed_count"] = method_config.get("failed_count", 0) + 1
            method_config["last_error"] = error
            method_config["last_attempt"] = datetime.now().isoformat()

            # 检查是否超过阈值
            if method_config["failed_count"] >= self.failed_threshold:
                method_config["supported"] = False
                logger.warning(f"Method {method} marked as unsupported after {method_config['failed_count']} failures")

            # 保存更新
            self.config.capabilities = capabilities
            await self.config.save()
