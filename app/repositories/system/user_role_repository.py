"""
用户-角色关联 Repository 层

提供 UserRole 关联表的数据访问操作，继承 BaseRepository 获得通用 CRUD 能力。
"""

from typing import List, Tuple

from app.core.ctx import Ctx
from app.models.admin import UserRole
from app.repositories.base_repository import BaseRepository


class UserRoleRepository(BaseRepository[UserRole]):
    """
    用户-角色关联 Repository

    继承 BaseRepository 获得通用 CRUD 能力。
    UserRole 是关联表，用于存储用户与角色的多对多关系。
    """

    def __init__(self):
        super().__init__(UserRole)

    async def get_role_ids_by_user_id(self, user_id: int) -> List[int]:
        """
        根据用户 ID 获取角色 ID 列表

        Args:
            user_id: 用户ID

        Returns:
            List[int]: 角色ID列表
        """
        rows = await self.get_queryset().filter(user_id=user_id).values("role_id")
        return [r["role_id"] for r in rows]

    async def get_user_ids_by_role_id(self, role_id: int) -> List[int]:
        """
        根据角色 ID 获取用户 ID 列表

        Args:
            role_id: 角色ID

        Returns:
            List[int]: 用户ID列表
        """
        rows = await self.get_queryset().filter(role_id=role_id).values("user_id")
        return [r["user_id"] for r in rows]

    async def batch_get_role_ids_by_user_ids(self, user_ids: List[int]) -> dict[int, List[int]]:
        """
        批量获取用户 ID -> 角色 ID 列表的映射

        Args:
            user_ids: 用户ID列表

        Returns:
            dict[int, List[int]]: 用户ID到角色ID列表的映射
        """
        rows = await self.get_queryset().filter(user_id__in=user_ids).values("user_id", "role_id")
        result: dict[int, List[int]] = {}
        for r in rows:
            result.setdefault(r["user_id"], []).append(r["role_id"])
        return result

    async def replace_user_roles(self, user_id: int, role_ids: List[int]) -> None:
        """
        替换用户的角色关联（先删除再批量插入）

        使用 BaseRepository 的默认租户过滤机制，无需手动判断租户ID
        注意：bulk_create 不会自动注入租户ID，需要从 Ctx 获取

        Args:
            user_id: 用户ID
            role_ids: 角色ID列表
        """
        # 删除现有记录（自动应用租户过滤）
        await self.get_queryset().filter(user_id=user_id).delete()

        # 批量创建新记录（从 Ctx 获取租户ID）
        if role_ids:
            tenant_id = Ctx.get_effective_tenant_id()
            create_data = [
                {"user_id": user_id, "role_id": rid, "tenant_id": tenant_id if tenant_id > 0 else None}
                for rid in set(role_ids)
            ]
            await self.model.bulk_create([self.model(**data) for data in create_data])

    async def delete_by_user_and_role(self, user_id: int, role_id: int) -> None:
        """
        删除用户-角色关联

        Args:
            user_id: 用户ID
            role_id: 角色ID
        """
        await self.get_queryset().filter(user_id=user_id, role_id=role_id).delete()

    async def batch_add_user_roles(self, user_id_role_id_pairs: List[Tuple[int, int, int]]) -> None:
        """
        批量添加用户-角色关联（自动去重）

        Args:
            user_id_role_id_pairs: (用户ID, 角色ID, 租户ID) 元组列表
        """
        if not user_id_role_id_pairs:
            return

        # 只查询相关用户的数据，减少查询范围
        user_ids = list(set(uid for uid, _, _ in user_id_role_id_pairs))
        existing = await self.get_queryset().filter(user_id__in=user_ids).values("user_id", "role_id")
        existing_set = {(r["user_id"], r["role_id"]) for r in existing}

        to_create = []
        for uid, rid, tid in user_id_role_id_pairs:
            if (uid, rid) not in existing_set:
                to_create.append(self.model(user_id=uid, role_id=rid, tenant_id=tid))
                existing_set.add((uid, rid))

        if to_create:
            await self.model.bulk_create(to_create)


# 全局 Repository 实例
user_role_repository = UserRoleRepository()
