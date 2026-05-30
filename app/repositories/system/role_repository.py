"""
角色 Repository 层

提供 Role 模型的数据访问操作，继承 BaseRepository 获得通用 CRUD 能力。
Role 有 tenant_id 字段，基类会自动处理租户过滤。
"""

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


# 全局 Repository 实例
role_repository = RoleRepository()
