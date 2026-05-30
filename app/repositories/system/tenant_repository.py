"""
租户 Repository 层

提供 Tenant 的数据访问操作，继承 BaseRepository 获得通用 CRUD 能力。
注意：Tenant 查询不需要租户过滤（超管查看所有租户）。
"""

from typing import Optional

from app.models.admin import Tenant
from app.repositories.base_repository import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    """
    租户 Repository

    继承 BaseRepository 获得通用 CRUD 能力：
    - get_by_id(id): 根据ID获取租户
    - get_by_ids(ids): 根据ID列表批量获取租户
    - get_all_by_tenant(): 获取所有租户（不过滤）
    - filter_by_kwargs(**kwargs): 根据条件筛选租户
    - create(obj_in): 创建租户
    - update(id, obj_in): 更新租户
    - delete(id): 删除租户

    注意：Tenant 查询不需要租户过滤（超管查看所有租户），
    通过设置 enable_tenant_filter = False 关闭自动过滤。
    """

    # 关闭租户过滤，Tenant 查询不需要租户隔离
    enable_tenant_filter = False

    def __init__(self):
        super().__init__(Tenant)

    async def get_by_domain(self, domain: str) -> Optional[Tenant]:
        """根据域名获取租户"""
        return await self.model.filter(domain=domain).first()


# 全局 Repository 实例
tenant_repository = TenantRepository()
