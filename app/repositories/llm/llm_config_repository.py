"""
LLMConfig Repository - LLM配置数据访问层

严格遵循技术约束文档：
- 继承 BaseRepository 获得通用 CRUD 能力
- LLMConfig 是全局配置，无租户过滤
- 禁止手动传递 tenant_id 参数
- 使用 self.filter() 进行链式查询
"""
from typing import List, Optional

from app.models.llm_config import LLMConfig
from app.repositories.base_repository import BaseRepository


class LLMConfigRepository(BaseRepository[LLMConfig]):
    """
    LLM配置 Repository

    职责：
    - LLM配置相关的数据访问操作
    - 继承 BaseRepository 获得通用 CRUD 能力
    - LLMConfig 是全局配置，关闭租户过滤

    约束：
    - 禁止直接查询 Model，使用 self.filter() 方法
    - 禁止手动传递 tenant_id 参数
    """

    # LLMConfig 是全局配置，不需要租户过滤
    enable_tenant_filter = False

    def __init__(self):
        super().__init__(LLMConfig)

    async def get_by_name(self, name: str) -> Optional[LLMConfig]:
        """
        根据名称获取配置

        Args:
            name: 配置名称

        Returns:
            LLMConfig 对象或 None
        """
        return await self.filter(name=name).first()

    async def get_active_configs(self) -> List[LLMConfig]:
        """
        获取所有启用的配置

        Returns:
            LLMConfig 列表
        """
        return await self.filter(is_active=True).all()

    async def get_default_config(self) -> Optional[LLMConfig]:
        """
        获取默认配置

        Returns:
            LLMConfig 对象或 None
        """
        return await self.filter(is_default=True, is_active=True).first()

    async def check_name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        """
        检查配置名称是否已存在

        Args:
            name: 配置名称
            exclude_id: 要排除的配置ID（用于更新时排除自身）

        Returns:
            是否存在
        """
        query = self.filter(name=name)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()

    async def get_by_provider(self, provider: str) -> List[LLMConfig]:
        """
        根据提供商获取配置列表

        Args:
            provider: 提供商名称

        Returns:
            LLMConfig 列表
        """
        return await self.filter(model_provider=provider, is_active=True).all()

    async def update_capabilities(self, config_id: int, capabilities: dict) -> Optional[LLMConfig]:
        """
        更新配置的能力字段

        Args:
            config_id: 配置ID
            capabilities: 能力配置字典

        Returns:
            更新后的 LLMConfig 对象或 None
        """
        return await self.update(config_id, {"capabilities": capabilities})

    async def update_gateway_model_id(self, config_id: int, gateway_model_id: str) -> Optional[LLMConfig]:
        """
        更新配置的网关模型ID

        Args:
            config_id: 配置ID
            gateway_model_id: LiteLLM网关中的模型ID

        Returns:
            更新后的 LLMConfig 对象或 None
        """
        return await self.update(config_id, {"gateway_model_id": gateway_model_id})

    def get_default_capabilities(self) -> dict:
        """
        获取默认能力配置

        Returns:
            默认能力配置字典
        """
        return self.model.get_default_capabilities()


# 创建全局仓库实例
llm_config_repository = LLMConfigRepository()
