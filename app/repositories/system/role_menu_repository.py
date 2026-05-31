"""
角色-菜单关联 Repository 层

提供 RoleMenu 关联表的数据访问操作，继承 BaseRepository 获得通用 CRUD 能力。
"""

from typing import List

from app.core.ctx import Ctx
from app.models.admin import RoleMenu
from app.repositories.base_repository import BaseRepository


class RoleMenuRepository(BaseRepository[RoleMenu]):
    """
    角色-菜单关联 Repository

    继承 BaseRepository 获得通用 CRUD 能力。
    RoleMenu 是关联表，用于存储角色与菜单的多对多关系。
    """

    def __init__(self):
        super().__init__(RoleMenu)

    async def get_menu_ids_by_role_id(self, role_id: int) -> List[int]:
        """
        根据角色 ID 获取菜单 ID 列表

        Args:
            role_id: 角色ID

        Returns:
            List[int]: 菜单ID列表
        """
        rows = await self.filter(role_id=role_id).values("menu_id")
        return [r["menu_id"] for r in rows]

    async def get_role_ids_by_menu_id(self, menu_id: int) -> List[int]:
        """
        根据菜单 ID 获取角色 ID 列表

        Args:
            menu_id: 菜单ID

        Returns:
            List[int]: 角色ID列表
        """
        rows = await self.filter(menu_id=menu_id).values("role_id")
        return [r["role_id"] for r in rows]

    async def batch_get_menu_ids_by_role_ids(self, role_ids: List[int]) -> dict[int, List[int]]:
        """
        批量获取角色 ID -> 菜单 ID 列表的映射

        Args:
            role_ids: 角色ID列表

        Returns:
            dict[int, List[int]]: 角色ID到菜单ID列表的映射
        """
        rows = await self.filter(role_id__in=role_ids).values("role_id", "menu_id")
        result: dict[int, List[int]] = {}
        for r in rows:
            result.setdefault(r["role_id"], []).append(r["menu_id"])
        return result

    async def replace_role_menus(self, role_id: int, menu_ids: List[int]) -> None:
        """
        替换角色的菜单关联（先删除再批量插入）

        Args:
            role_id: 角色ID
            menu_ids: 菜单ID列表

        注意：tenant_id 从 Ctx 获取，不需要外部传递
        """
        tenant_id = Ctx.get_effective_tenant_id()

        # 删除现有关联
        await self.filter(role_id=role_id).delete()

        # 批量创建新关联
        if menu_ids:
            await self.model.bulk_create(
                [self.model(role_id=role_id, menu_id=mid, tenant_id=tenant_id) for mid in set(menu_ids)]
            )


# 全局 Repository 实例
role_menu_repository = RoleMenuRepository()
