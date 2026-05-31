"""
菜单 Repository 层

提供菜单相关的数据访问操作，继承 BaseRepository 获得通用 CRUD 能力。
Menu 模型没有 tenant_id 字段，关闭自动租户过滤。
"""

from typing import List, Optional, Set

from tortoise.expressions import Q

from app.models.admin import Menu
from app.repositories.base_repository import BaseRepository
from app.repositories.system.role_menu_repository import role_menu_repository
from app.repositories.system.user_role_repository import user_role_repository


class MenuRepository(BaseRepository[Menu]):
    """
    菜单 Repository

    继承 BaseRepository 获得通用 CRUD 能力。
    Menu 模型没有 tenant_id 字段，关闭自动租户过滤。
    """

    # 关闭租户过滤，Menu 模型没有 tenant_id 字段
    enable_tenant_filter = False

    def __init__(self):
        super().__init__(Menu)

    async def get_all_ids(self) -> List[int]:
        """获取所有菜单ID"""
        return await self.filter().values_list("id", flat=True)

    async def get_by_ids(self, menu_ids: List[int]) -> List[Menu]:
        """根据ID列表获取菜单"""
        if not menu_ids:
            return []
        return await self.filter(id__in=menu_ids).all()

    async def get_all(self) -> List[Menu]:
        """获取所有菜单"""
        return await self.filter().all()

    async def get_user_menu_ids(self, user_id: int) -> Set[int]:
        """
        获取用户在当前租户下的所有菜单ID

        自动应用租户过滤（通过 role_menu_repository 继承自 BaseRepository）

        Args:
            user_id: 用户ID

        Returns:
            Set[int]: 菜单ID集合
        """
        if not user_id:
            return set()

        role_ids = await user_role_repository.get_role_ids_by_user_id(user_id)
        if not role_ids:
            return set()

        rows = await role_menu_repository.batch_get_menu_ids_by_role_ids(role_ids)
        menu_ids: Set[int] = set()
        for rid, mids in rows.items():
            menu_ids.update(mids)
        return menu_ids

    async def get_by_path(self, path: str) -> Optional[Menu]:
        """
        根据路径获取菜单

        Args:
            path: 菜单路径

        Returns:
            Optional[Menu]: 菜单对象，不存在返回None
        """
        return await self.filter(path=path).first()

    async def get_children_count(self, parent_id: int) -> int:
        """
        获取子菜单数量

        Args:
            parent_id: 父菜单ID

        Returns:
            int: 子菜单数量
        """
        return await self.filter(parent_id=parent_id).count()

    async def get_parent_menus(self) -> List[Menu]:
        """
        获取所有父级菜单（parent_id=0）

        Returns:
            List[Menu]: 父级菜单列表
        """
        return await self.filter(parent_id=0).order_by("order").all()

    async def list_with_permission(
        self,
        user_id: int,
        is_superuser: bool,
        page: int = 1,
        page_size: int = 10
    ) -> tuple[int, List[Menu]]:
        """
        根据用户权限获取菜单列表

        Args:
            user_id: 用户ID
            is_superuser: 是否为超级管理员
            page: 页码
            page_size: 每页数量

        Returns:
            tuple[int, List[Menu]]: (总数, 菜单列表)
        """
        if is_superuser:
            total = await self.filter().count()
            menus = await self.filter().order_by("order").offset((page - 1) * page_size).limit(page_size)
            return total, list(menus)

        menu_ids = await self.get_user_menu_ids(user_id)
        if not menu_ids:
            return 0, []

        total = len(menu_ids)
        menus = await self.filter(id__in=list(menu_ids)).order_by("order").offset((page - 1) * page_size).limit(page_size)
        return total, list(menus)


# 全局 Repository 实例
menu_repository = MenuRepository()
