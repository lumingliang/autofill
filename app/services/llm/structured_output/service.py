"""
结构化输出服务主类
"""
import time
from datetime import datetime
from typing import Any, Dict, List

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

    # 方法名到方法函数的映射（排除 plain，因为它参数签名不同）
    _METHOD_MAP = {
        "with_structured_output": "method_with_structured_output",
        "bind_tools_non_stream": "method_bind_tools_non_stream",
        "bind_tools_stream": "method_bind_tools_stream",
        "custom_fc_non_stream": "method_custom_fc_non_stream",
        "custom_fc_stream": "method_custom_fc_stream",
        "pydantic_parser": "method_pydantic_parser",
        "json_parser": "method_json_parser",
    }

    def __init__(self, config: LLMConfig):
        self.config = config
        self.model_name = config.model  # 使用自动拼接的模型名称
        self.api_key = config.api_key or ""
        self.api_base = config.api_base or None
        self.timeout = config.timeout or 300

        # 获取结构化输出配置
        self.structured_config = settings.STRUCTURED_OUTPUT_CONFIG
        self.failed_threshold = self.structured_config.get("failed_threshold", 2)
        self.enable_fallback = self.structured_config.get("enable_fallback", True)
        self.max_attempt_methods = self.structured_config.get("max_attempt_methods", 6)

        # 初始化方法执行器
        litellm_config = settings.LITELLM_CONFIG
        base_url = litellm_config.get("base_url")
        master_key = litellm_config.get("master_key")

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
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto",
        method: str = None,
        field_specs: List[Dict[str, Any]] = None,
        include_reason: bool = False,
        full_system_prompt: str = None
    ) -> StructuredOutputResult:
        """
        生成结构化输出，支持多轮对话记忆
        """
        start_time = time.time()

        # 使用指定的方法
        try:
            result = await self._try_method(
                method=method,
                query=query,
                tools=tools,
                system_prompt=system_prompt,
                session_id=session_id,
                memory_rounds=memory_rounds,
                tool_choice=tool_choice,
                field_specs=field_specs,
                include_reason=include_reason,
                full_system_prompt=full_system_prompt
            )
            if result.success:
                result.latency_ms = int((time.time() - start_time) * 1000)
            return result
        except Exception as e:
            logger.error(f"Method {method} failed: {type(e).__name__}: {e}")
            return StructuredOutputResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                method=method
            )

    async def _try_method(
        self,
        method: str,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto",
        field_specs: List[Dict[str, Any]] = None,
        include_reason: bool = False,
        full_system_prompt: str = None
    ) -> StructuredOutputResult:
        """尝试使用指定方法"""
        # plain 模式特殊处理（参数签名不同）
        if method == "plain":
            return await self.methods.method_plain(
                query=query,
                system_prompt=full_system_prompt or system_prompt,
                field_specs=field_specs,
                include_reason=include_reason,
                session_id=session_id,
                memory_rounds=memory_rounds,
                history_manager=self._history_manager
            )

        if method not in self._METHOD_MAP:
            return StructuredOutputResult(
                success=False,
                error=f"未知方法: {method}",
                method=method
            )

        # 获取方法函数
        method_func = getattr(self.methods, self._METHOD_MAP[method])

        # 构建通用参数
        call_kwargs = {
            "query": query,
            "tools": tools,
            "session_id": session_id,
            "memory_rounds": memory_rounds,
            "tool_choice": tool_choice,
            "history_manager": self._history_manager,
        }

        # json_parser 方法使用 full_system_prompt，其他方法使用 system_prompt
        if method == "json_parser":
            call_kwargs["system_prompt"] = full_system_prompt or system_prompt
        else:
            call_kwargs["system_prompt"] = system_prompt

        return await method_func(**call_kwargs)

    async def _record_method_failure(self, method: str, error: str):
        """记录方法失败"""
        from app.repositories.llm.llm_config_repository import llm_config_repository

        capabilities = self.config.capabilities or llm_config_repository.get_default_capabilities()
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

            # 保存更新（通过 Repository 层）
            await llm_config_repository.update_capabilities(self.config.id, capabilities)
