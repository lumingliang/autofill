"""
角色-API关联 Repository 层

提供 RoleApi 关联表的数据访问操作，继承 BaseRepository 获得通用 CRUD 能力。
"""

from typing import List

from app.models.admin import RoleApi
from app.repositories.base_repository import BaseRepository


class RoleApiRepository(BaseRepository[RoleApi]):
    """
    角色-API关联 Repository

    继承 BaseRepository 获得通用 CRUD 能力。
    RoleApi 是关联表，用于存储角色与API的多对多关系。
    """

    def __init__(self):
        super().__init__(RoleApi)

    async def get_api_ids_by_role_id(self, role_id: int) -> List[int]:
        """
        根据角色 ID 获取 API ID 列表

        Args:
            role_id: 角色ID

        Returns:
            List[int]: API ID列表
        """
        rows = await self.get_queryset().filter(role_id=role_id).values("api_id")
        return [r["api_id"] for r in rows]

    async def get_role_ids_by_api_id(self, api_id: int) -> List[int]:
        """
        根据 API ID 获取角色 ID 列表

        Args:
            api_id: API ID

        Returns:
            List[int]: 角色ID列表
        """
        rows = await self.get_queryset().filter(api_id=api_id).values("role_id")
        return [r["role_id"] for r in rows]

    async def batch_get_api_ids_by_role_ids(self, role_ids: List[int]) -> dict[int, List[int]]:
        """
        批量获取角色 ID -> API ID 列表的映射

        Args:
            role_ids: 角色ID列表

        Returns:
            dict[int, List[int]]: 角色ID到API ID列表的映射
        """
        rows = await self.get_queryset().filter(role_id__in=role_ids).values("role_id", "api_id")
        result: dict[int, List[int]] = {}
        for r in rows:
            result.setdefault(r["role_id"], []).append(r["api_id"])
        return result

    async def replace_role_apis(self, role_id: int, api_ids: List[int], tenant_id: int) -> None:
        """
        替换角色的 API 关联（先删除再批量插入）

        Args:
            role_id: 角色ID
            api_ids: API ID列表
            tenant_id: 租户ID
        """
        await self.get_queryset().filter(role_id=role_id, tenant_id=tenant_id).delete()

        if api_ids:
            await self.model.bulk_create(
                [self.model(role_id=role_id, api_id=aid, tenant_id=tenant_id) for aid in set(api_ids)]
            )


# 全局 Repository 实例
role_api_repository = RoleApiRepository()
