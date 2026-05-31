"""
审计日志 Repository 层

提供审计日志相关的数据访问操作，继承 BaseRepository 获得通用 CRUD 能力。
AuditLog 模型有 tenant_id 字段，自动应用租户过滤。
"""
from typing import List, Tuple
from tortoise.expressions import Q

from app.models.admin import AuditLog
from app.repositories.base_repository import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """
    审计日志 Repository

    继承 BaseRepository 获得通用 CRUD 能力。
    AuditLog 模型有 tenant_id 字段，自动应用租户过滤。
    """

    def __init__(self):
        super().__init__(AuditLog)

    async def list_with_filter(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Q = None,
        order: List[str] = None
    ) -> Tuple[int, List[AuditLog]]:
        """
        根据条件查询审计日志列表

        Args:
            page: 页码
            page_size: 每页数量
            search: 查询条件（Q对象）
            order: 排序字段列表

        Returns:
            Tuple[int, List[AuditLog]]: (总数, 日志列表)
        """
        if order is None:
            order = ["-created_at"]

        # 构建基础查询
        query = self.filter(search) if search else self.filter()

        # 获取总数
        total = await query.count()

        # 获取分页数据
        logs = await query.offset((page - 1) * page_size).limit(page_size).order_by(*order)

        return total, logs

    async def count_with_filter(self, search: Q = None) -> int:
        """
        根据条件统计审计日志数量

        Args:
            search: 查询条件（Q对象）

        Returns:
            int: 数量
        """
        query = self.filter(search) if search else self.filter()
        return await query.count()


# 全局 Repository 实例
audit_log_repository = AuditLogRepository()
