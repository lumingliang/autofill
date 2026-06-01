"""
Dify Agent Repository - Dify Agent 数据访问层

严格遵循技术约束文档：
- 继承 BaseRepository 获得通用 CRUD 能力
- 自动应用租户过滤（通过 BaseRepository）
- 禁止手动传递 tenant_id 参数
- 使用 self.filter() 进行链式查询
"""
from typing import List, Optional

from app.models.dify_agent import DifyAgent
from app.repositories.base_repository import BaseRepository


class DifyAgentRepository(BaseRepository[DifyAgent]):
    """
    Dify Agent Repository

    职责：
    - Dify Agent 相关的数据访问操作
    - 继承 BaseRepository 获得通用 CRUD 能力
    - 自动应用租户过滤

    约束：
    - 禁止直接查询 Model，使用 self.filter() 方法
    - 禁止手动传递 tenant_id 参数，从 Ctx 获取
    """

    def __init__(self):
        super().__init__(DifyAgent)

    async def get_by_api_key(self, api_key: str) -> Optional[DifyAgent]:
        """
        根据 API Key 获取 Agent

        用于 public 接口查询，不应用租户过滤

        Args:
            api_key: Dify API Key

        Returns:
            DifyAgent 对象或 None
        """
        return await self.model.get_or_none(api_key=api_key, is_active=True)

    async def check_name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        """
        检查 Agent 名称是否已存在

        自动应用租户过滤（通过 self.filter）

        Args:
            name: Agent 名称
            exclude_id: 排除的ID（用于更新时检查）

        Returns:
            bool: 是否存在
        """
        query = self.filter(name=name)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()

    async def list_active_agents(self) -> List[DifyAgent]:
        """
        获取所有启用的 Agent 列表

        自动应用租户过滤（通过 self.filter）

        Returns:
            DifyAgent 列表
        """
        return await self.filter(is_active=True).all()


# Repository 实例
dify_agent_repository = DifyAgentRepository()
