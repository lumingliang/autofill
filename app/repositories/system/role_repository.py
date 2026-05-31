"""
角色 Repository 层

提供 Role 模型的数据访问操作，继承 BaseRepository 获得通用 CRUD 能力。
Role 有 tenant_id 字段，基类会自动处理租户过滤。
"""

from typing import List

from tortoise.expressions import Q

from app.models.admin import Role
from app.repositories.base_repository import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """
    角色 Repository

    继承 BaseRepository 获得通用 CRUD 能力：
    - get_by_id(id): 根据ID获取角色
    - get_by_ids(ids): 根据ID列表批量获取角色
    - get_all_by_tenant(): 获取当前租户下的所有角色
    - filter_by_kwargs(**kwargs): 根据条件筛选角色
    - create(obj_in): 创建角色
    - update(id, obj_in): 更新角色
    - delete(id): 删除角色

    所有方法自动应用租户过滤。
    """

    def __init__(self):
        super().__init__(Role)

    async def get_by_name(self, name: str):
        """根据名称获取角色（应用租户过滤）"""
        return await self.filter(name=name).first()

    async def list_by_name(
        self,
        page: int = 1,
        page_size: int = 10,
        role_name: str = "",
        order: List[str] = None
    ):
        """
        根据名称模糊查询角色列表

        Args:
            page: 页码
            page_size: 每页数量
            role_name: 角色名称模糊查询
            order: 排序字段列表

        Returns:
            Tuple[int, List[Role]]: (总数, 角色列表)
        """
        query = self.filter()

        if role_name:
            query = query.filter(name__contains=role_name)

        total = await query.count()

        if order:
            query = query.order_by(*order)

        roles = await query.offset((page - 1) * page_size).limit(page_size).all()

        return total, roles

    async def exists_by_ids_and_tenant(self, role_ids: List[int], tenant_id: int) -> bool:
        """
        检查指定ID列表中是否存在指定租户的角色

        Args:
            role_ids: 角色ID列表
            tenant_id: 租户ID

        Returns:
            bool: 是否存在
        """
        return await self.filter(
            id__in=role_ids,
            tenant_id=tenant_id
        ).exists()


# 全局 Repository 实例
role_repository = RoleRepository()
