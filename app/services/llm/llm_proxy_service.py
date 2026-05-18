"""
LLM 代理服务 - 统一的结构化输出调用入口
"""
from typing import Any, Dict, List, Optional

from app.models.llm_config import LLMConfig
from app.services.llm.structured_output.service import StructuredOutputService


class LLMProxyService:
    """LLM 代理服务 - 提供统一的结构化输出调用接口"""

    async def process_request(
        self,
        query: str,
        tools: List[Dict[str, Any]] = None,
        system_prompt: str = None,
        tool_choice: str = "auto",
        method: str = None,
        config: LLMConfig = None,
        session_id: str = None,
        memory_rounds: int = None,
        full_system_prompt: str = None
    ) -> Dict[str, Any]:
        """
        处理 LLM 结构化输出请求

        Args:
            query: 用户查询
            tools: FC Schema 工具列表（plain 方法可不传）
            system_prompt: 系统提示词
            tool_choice: 工具选择策略
            method: 指定使用的结构化输出方法
            config: LLM 配置
            session_id: 会话 ID
            memory_rounds: 记忆轮数
            full_system_prompt: 完整的系统提示词（包含字段指引，用于 json_parser 方法）

        Returns:
            Dict 包含处理结果
        """
        # plain 方法不需要 tools
        if method != "plain" and not tools:
            raise ValueError("tools 参数不能为空（plain 方法除外）")

        if not config:
            raise ValueError("config 参数不能为空")

        service = StructuredOutputService(config)

        result = await service.generate(
            query=query,
            tools=tools or [],
            system_prompt=system_prompt,
            session_id=session_id,
            memory_rounds=memory_rounds,
            tool_choice=tool_choice,
            method=method,
            full_system_prompt=full_system_prompt
        )

        return {
            "success": result.success,
            "data": result.data,
            "error": result.error,
            "method": result.method,
            "latency_ms": result.latency_ms
        }


# 全局服务实例
llm_proxy_service = LLMProxyService()
