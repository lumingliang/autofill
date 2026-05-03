"""
LLM 代理服务
处理 LLM 代理请求
"""
from typing import Any, Dict, List, Optional

from app.log import logger
from app.models.llm_config import LLMConfig
from app.services.llm.structured_output import StructuredOutputResult, StructuredOutputService
from app.services.llm.llm_config_utils import get_default_llm_config


class LLMProxyService:
    """LLM 代理服务"""

    async def process_request(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        config: LLMConfig = None,
        session_id: str = None,
        memory_rounds: int = None,
        tool_choice: str = "auto",
        method: str = None,
        tenant_id: int = 0,
        app_name: str = None
    ) -> Dict[str, Any]:
        """
        处理 LLM 代理请求

        Args:
            query: 用户查询
            tools: 工具/函数定义列表
            system_prompt: 系统提示词
            config: LLM 配置，如果为 None 则使用默认配置
            session_id: 会话ID，用于多轮对话记忆
            memory_rounds: 记忆轮数限制
            tool_choice: 工具选择模式，可选 "auto", "none", "required" 或指定工具名
            method: 指定使用的方法，可选 "with_structured_output", "bind_tools_stream",
                   "custom_fc_non_stream", "custom_fc_stream", "pydantic_parser", "json_parser"
            tenant_id: 租户ID
            app_name: 应用名称

        Returns:
            Dict: 包含结构化输出结果和元信息
        """
        # 获取配置
        if config is None:
            config = await get_default_llm_config(tenant_id=tenant_id, app_name=app_name)
            if config is None:
                raise ValueError("No LLM configuration found")

        # 创建结构化输出服务
        service = StructuredOutputService(config)

        # 生成结构化输出（支持多轮对话记忆）
        result = await service.generate(
            query=query,
            tools=tools,
            system_prompt=system_prompt,
            session_id=session_id,
            memory_rounds=memory_rounds,
            tool_choice=tool_choice,
            method=method
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
            config = await get_default_llm_config()
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
