"""
LLM 代理服务
处理 LLM 代理请求
"""
import logging
from typing import Any, Dict, List, Optional

from app.controllers.llm_config import llm_config_controller
from app.models.llm_config import LLMConfig
from app.services.llm.structured_output import StructuredOutputResult, StructuredOutputService

logger = logging.getLogger(__name__)


class LLMProxyService:
    """LLM 代理服务"""

    async def process_request(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        tool_choice: str = "auto",
        context: str = None,
        preferred_methods: List[str] = None,
        config: LLMConfig = None
    ) -> Dict[str, Any]:
        """
        处理 LLM 代理请求

        Args:
            query: 用户查询
            tools: 工具/函数定义列表
            system_prompt: 系统提示词
            tool_choice: 工具选择策略
            context: 额外上下文
            preferred_methods: 优先使用方法列表
            config: LLM 配置，如果为 None 则使用默认配置

        Returns:
            Dict: 包含结构化输出结果和元信息
        """
        # 获取配置
        if config is None:
            config = await llm_config_controller.get_default_config()
            if config is None:
                raise ValueError("No LLM configuration found")

        # 创建结构化输出服务
        service = StructuredOutputService(config)

        # 生成结构化输出
        result = await service.generate(
            query=query,
            tools=tools,
            system_prompt=system_prompt,
            context=context,
            preferred_methods=preferred_methods
        )

        if not result.success:
            raise ValueError(f"Failed to generate structured output: {result.error}")

        # 构建响应
        response_data = result.data.copy()

        # 添加元信息
        response_data["_meta"] = {
            "method_used": result.method,
            "model": config.litellm_params.get("model", "unknown"),
            "latency_ms": result.latency_ms,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens
        }

        return response_data

    async def health_check(self, config: LLMConfig = None) -> Dict[str, Any]:
        """
        健康检查

        Args:
            config: LLM 配置，如果为 None 则使用默认配置

        Returns:
            Dict: 健康检查结果
        """
        if config is None:
            config = await llm_config_controller.get_default_config()
            if config is None:
                return {
                    "status": "unhealthy",
                    "error": "No LLM configuration found"
                }

        return {
            "status": "healthy",
            "tenant_id": config.tenant_id,
            "app_name": config.app_name,
            "llm_config": {
                "name": config.name,
                "model": config.litellm_params.get("model", "unknown")
            }
        }


# 全局服务实例
llm_proxy_service = LLMProxyService()
