"""
部门闭包 Repository 层

提供 DeptClosure 关联表的数据访问操作，继承 BaseRepository 获得通用 CRUD 能力。
"""

from typing import List

from app.models.admin import DeptClosure
from app.repositories.base_repository import BaseRepository


class DeptClosureRepository(BaseRepository[DeptClosure]):
    """
    部门闭包 Repository

    继承 BaseRepository 获得通用 CRUD 能力。
    DeptClosure 是关联表，用于存储部门层级关系。
    """

    def __init__(self):
        super().__init__(DeptClosure)

    async def get_descendant_ids(self, ancestor_id: int) -> List[int]:
        """
        获取指定部门的所有后代部门ID

        Args:
            ancestor_id: 祖先部门ID

        Returns:
            List[int]: 后代部门ID列表
        """
        return await self.filter(ancestor=ancestor_id).values_list("descendant", flat=True)

    async def get_ancestor_ids(self, descendant_id: int) -> List[int]:
        """
        获取指定部门的所有祖先部门ID

        Args:
            descendant_id: 后代部门ID

        Returns:
            List[int]: 祖先部门ID列表
        """
        return await self.filter(descendant=descendant_id).values_list("ancestor", flat=True)


# 全局 Repository 实例
dept_closure_repository = DeptClosureRepository()
