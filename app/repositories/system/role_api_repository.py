"""
角色-API关联 Repository 层

提供 RoleApi 关联表的数据访问操作，继承 BaseRepository 获得通用 CRUD 能力。
"""

from typing import List, Tuple

from app.core.ctx import Ctx
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
        rows = await self.filter(role_id=role_id).values("api_id")
        return [r["api_id"] for r in rows]

    async def get_role_ids_by_api_id(self, api_id: int) -> List[int]:
        """
        根据 API ID 获取角色 ID 列表

        Args:
            api_id: API ID

        Returns:
            List[int]: 角色ID列表
        """
        rows = await self.filter(api_id=api_id).values("role_id")
        return [r["role_id"] for r in rows]

    async def batch_get_api_ids_by_role_ids(self, role_ids: List[int]) -> dict[int, List[int]]:
        """
        批量获取角色 ID -> API ID 列表的映射

        自动应用租户过滤（继承自 BaseRepository）

        Args:
            role_ids: 角色ID列表

        Returns:
            dict[int, List[int]]: 角色ID到API ID列表的映射
        """
        rows = await self.filter(role_id__in=role_ids).values("role_id", "api_id")
        result: dict[int, List[int]] = {}
        for r in rows:
            result.setdefault(r["role_id"], []).append(r["api_id"])
        return result

    async def replace_role_apis(self, role_id: int, api_ids: List[int]) -> None:
        """
        替换角色的 API 关联（先删除再批量插入）

        Args:
            role_id: 角色ID
            api_ids: API ID列表

        注意：tenant_id 从 Ctx 获取，不需要外部传递
        """
        tenant_id = Ctx.get_effective_tenant_id()

        # 删除现有关联
        await self.filter(role_id=role_id).delete()

        # 批量创建新关联
        if api_ids:
            await self.model.bulk_create(
                [self.model(role_id=role_id, api_id=aid, tenant_id=tenant_id) for aid in set(api_ids)]
            )

    async def batch_add_role_apis(
        self, role_id_api_id_pairs: List[Tuple[int, int]], tenant_id: int = None
    ) -> None:
        """
        批量添加角色-API关联（自动去重）

        Args:
            role_id_api_id_pairs: (角色ID, API ID) 元组列表
            tenant_id: 租户ID，如果不传则从 Ctx 获取
        """
        if not role_id_api_id_pairs:
            return

        # 获取租户ID
        if tenant_id is None:
            tenant_id = Ctx.get_request_tenant_id()

        # 只查询相关角色的数据，减少查询范围
        role_ids = list(set(rid for rid, _ in role_id_api_id_pairs))
        existing = await self.filter(role_id__in=role_ids).values("role_id", "api_id")
        existing_set = {(r["role_id"], r["api_id"]) for r in existing}

        to_create = []
        for rid, aid in role_id_api_id_pairs:
            if (rid, aid) not in existing_set:
                to_create.append(self.model(role_id=rid, api_id=aid, tenant_id=tenant_id))
                existing_set.add((rid, aid))

        if to_create:
            await self.model.bulk_create(to_create)

    async def delete_by_api_ids(self, api_ids: List[int]) -> int:
        """
        根据API ID列表删除所有关联（直接操作模型，绕过租户过滤）

        用于API删除时的级联清理

        Args:
            api_ids: API ID列表

        Returns:
            int: 删除的记录数
        """
        if not api_ids:
            return 0
        # 直接使用 model.filter 绕过租户过滤
        deleted_count = await self.model.filter(api_id__in=api_ids).delete()
        return deleted_count


# 全局 Repository 实例
role_api_repository = RoleApiRepository()
