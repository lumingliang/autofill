"""
LLMProvider Repository - LLM提供商数据访问层

严格遵循技术约束文档：
- 继承 BaseRepository 获得通用 CRUD 能力
- LLMProvider 是全局配置，无租户过滤
- 禁止手动传递 tenant_id 参数
- 使用 self.filter() 进行链式查询
"""
from typing import List, Optional

from app.models.llm_config import LLMProvider
from app.repositories.base_repository import BaseRepository


class LLMProviderRepository(BaseRepository[LLMProvider]):
    """
    LLM提供商 Repository

    职责：
    - LLM提供商相关的数据访问操作
    - 继承 BaseRepository 获得通用 CRUD 能力
    - LLMProvider 是全局配置，关闭租户过滤

    约束：
    - 禁止直接查询 Model，使用 self.filter() 方法
    - 禁止手动传递 tenant_id 参数
    """

    # LLMProvider 是全局配置，不需要租户过滤
    enable_tenant_filter = False

    def __init__(self):
        super().__init__(LLMProvider)

    async def get_active_providers(self) -> List[LLMProvider]:
        """
        获取所有启用的提供商

        Returns:
            LLMProvider 列表（按 order 和 id 排序）
        """
        return await self.filter(is_active=True).order_by("order", "id")

    async def get_by_code(self, code: str) -> Optional[LLMProvider]:
        """
        根据代码获取提供商

        Args:
            code: 提供商代码

        Returns:
            LLMProvider 对象或 None
        """
        return await self.filter(code=code).first()


# 创建全局仓库实例
llm_provider_repository = LLMProviderRepository()
