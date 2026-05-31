"""
LLM 配置 Service 层
提供 LLM 配置相关的业务逻辑，供 Controller 和 Handler 复用
"""
from typing import Optional

from app.models.llm_config import LLMConfig
from app.repositories.llm.llm_config_repository import llm_config_repository


class LLMConfigService:
    """LLM 配置服务（全局配置）"""

    @staticmethod
    async def get_default_config() -> Optional[LLMConfig]:
        """
        获取默认 LLM 配置

        Returns:
            LLMConfig 实例或 None
        """
        return await llm_config_repository.get_default_config()


# 全局服务实例
llm_config_service = LLMConfigService()
