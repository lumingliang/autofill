"""
菜单 Repository 层

提供菜单相关的数据访问操作，继承 BaseRepository 获得通用 CRUD 能力。
Menu 模型没有 tenant_id 字段，关闭自动租户过滤。
"""

from typing import List

from app.models.admin import Menu
from app.repositories.base_repository import BaseRepository


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
        return await self.model.all().values_list("id", flat=True)

    async def get_by_ids(self, menu_ids: List[int]) -> List[Menu]:
        """根据ID列表获取菜单"""
        if not menu_ids:
            return []
        return await self.model.filter(id__in=menu_ids).all()


# 全局 Repository 实例
menu_repository = MenuRepository()
