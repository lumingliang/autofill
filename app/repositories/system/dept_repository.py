"""
部门 Repository 层

提供 Dept 的数据访问操作，继承 BaseRepository 获得通用 CRUD 能力。
Dept 有 tenant_id 字段，基类会自动处理租户过滤。
"""

from app.models.admin import Dept
from app.repositories.base_repository import BaseRepository


class DeptRepository(BaseRepository[Dept]):
    """
    部门 Repository

    继承 BaseRepository 获得通用 CRUD 能力：
    - get_by_id(id): 根据ID获取部门
    - get_by_ids(ids): 根据ID列表批量获取部门
    - get_all_by_tenant(): 获取当前租户下的所有部门
    - filter_by_kwargs(**kwargs): 根据条件筛选部门
    - create(obj_in): 创建部门
    - update(id, obj_in): 更新部门
    - delete(id): 删除部门

    所有方法自动应用租户过滤。
    """

    def __init__(self):
        super().__init__(Dept)


# 全局 Repository 实例
dept_repository = DeptRepository()
