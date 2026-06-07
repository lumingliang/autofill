"""
用户-租户关联 Repository 层

提供用户与租户关联的数据访问操作，继承 BaseRepository 获得通用 CRUD 能力。
UserTenant 有 tenant_id 字段，基类会自动处理租户过滤。
"""

from typing import List, Tuple

from app.models.admin import UserTenant
from app.repositories.base_repository import BaseRepository


class UserTenantRepository(BaseRepository[UserTenant]):
    """
    用户-租户关联 Repository

    继承 BaseRepository 获得通用 CRUD 能力。
    UserTenant 模型有 tenant_id 字段，基类会自动处理租户过滤。
    """

    def __init__(self):
        super().__init__(UserTenant)

    async def get_user_ids_by_tenant(self) -> List[int]:
        """获取当前租户下的所有用户ID（自动应用租户过滤）"""
        return await self.filter().values_list("user_id", flat=True)

    async def exists_by_user_id(self, user_id: int) -> bool:
        """
        检查用户是否在当前租户下（自动应用租户过滤）

        Args:
            user_id: 用户ID

        Returns:
            bool: 是否存在
        """
        return await self.filter(user_id=user_id).exists()

    async def get_tenant_ids_by_user_id(self, user_id: int) -> List[int]:
        """
        根据用户 ID 获取租户 ID 列表（直接查询模型，不应用租户过滤）

        注意：此方法查询用户的租户关联关系，不应被租户过滤限制

        Args:
            user_id: 用户ID

        Returns:
            List[int]: 租户ID列表
        """
        rows = await self.model.filter(user_id=user_id).values("tenant_id")
        return [r["tenant_id"] for r in rows]

    async def batch_get_tenant_ids_by_user_ids(self, user_ids: List[int]) -> dict[int, List[int]]:
        """
        批量获取用户 ID -> 租户 ID 列表的映射（直接查询模型，不应用租户过滤）

        注意：此方法查询用户的租户关联关系，不应被租户过滤限制

        Args:
            user_ids: 用户ID列表

        Returns:
            dict[int, List[int]]: 用户ID到租户ID列表的映射
        """
        rows = await self.model.filter(user_id__in=user_ids).values("user_id", "tenant_id")
        result: dict[int, List[int]] = {}
        for r in rows:
            result.setdefault(r["user_id"], []).append(r["tenant_id"])
        return result

    async def get_user_ids_by_tenant_id(self, tenant_id: int) -> List[int]:
        """
        获取指定租户下的所有用户ID（禁用租户过滤，用于超管查询）

        Args:
            tenant_id: 租户ID

        Returns:
            List[int]: 用户ID列表
        """
        # 直接使用 model.filter 绕过租户过滤
        return await self.model.filter(tenant_id=tenant_id).values_list("user_id", flat=True)

    async def get_all_by_tenant_id(self, tenant_id: int) -> List[UserTenant]:
        """
        获取指定租户下的所有用户关联（禁用租户过滤，用于超管查询）

        Args:
            tenant_id: 租户ID

        Returns:
            List[UserTenant]: 用户-租户关联列表
        """
        # 直接使用 model.filter 绕过租户过滤
        return await self.model.filter(tenant_id=tenant_id).all()

    async def delete_by_user_and_tenant(self, user_id: int, tenant_id: int) -> None:
        """
        删除用户-租户关联

        Args:
            user_id: 用户ID
            tenant_id: 租户ID
        """
        await self.model.filter(user_id=user_id, tenant_id=tenant_id).delete()

    async def batch_add_user_tenants(self, user_id_tenant_id_pairs: List[Tuple[int, int]]) -> None:
        """
        批量添加用户-租户关联（自动去重）

        Args:
            user_id_tenant_id_pairs: (用户ID, 租户ID) 元组列表
        """
        if not user_id_tenant_id_pairs:
            return

        # 只查询相关用户的数据，减少查询范围
        user_ids = list(set(uid for uid, _ in user_id_tenant_id_pairs))
        existing = await self.filter(user_id__in=user_ids).values("user_id", "tenant_id")
        existing_set = {(r["user_id"], r["tenant_id"]) for r in existing}

        to_create = []
        for uid, tid in user_id_tenant_id_pairs:
            if (uid, tid) not in existing_set:
                to_create.append(self.model(user_id=uid, tenant_id=tid))
                existing_set.add((uid, tid))

        if to_create:
            await self.model.bulk_create(to_create)


# 全局 Repository 实例
user_tenant_repository = UserTenantRepository()
