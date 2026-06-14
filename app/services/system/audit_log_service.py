"""
审计日志 Service 层

处理审计日志相关的业务逻辑，包括：
- 审计日志查询
- 租户过滤逻辑

约束：
- 不直接查询 Model 层，通过 Repository 层访问数据
- 租户信息从 Ctx 获取
"""
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException
from tortoise.expressions import Q

from app.core.ctx import Ctx
from app.core.dependency import is_superuser
from app.models.admin import AuditLog
from app.repositories.system.audit_log_repository import audit_log_repository


class AuditLogService:
    """
    审计日志 Service

    职责：
    - 处理审计日志查询业务逻辑
    - 管理租户过滤逻辑
    - 调用 Repository 层进行数据操作

    约束：
    - 不直接操作数据库，通过 Repository 层访问数据
    - 不处理 HTTP 请求/响应
    """

    async def list_audit_logs(
        self,
        page: int = 1,
        page_size: int = 10,
        username: str = "",
        module: str = "",
        method: str = "",
        summary: str = "",
        path: str = "",
        status: int = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> Tuple[int, List[AuditLog]]:
        """
        查询审计日志列表

        Args:
            page: 页码
            page_size: 每页数量
            username: 操作人名称模糊查询
            module: 功能模块模糊查询
            method: 请求方法模糊查询
            summary: 接口描述模糊查询
            path: 请求路径模糊查询
            status: 状态码
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            Tuple[int, List[AuditLog]]: (总数, 日志列表)
        """
        # 构建查询条件
        q = Q()
        if username:
            q &= Q(username__icontains=username)
        if module:
            q &= Q(module__icontains=module)
        if method:
            q &= Q(method__icontains=method)
        if summary:
            q &= Q(summary__icontains=summary)
        if path:
            q &= Q(path__icontains=path)
        if status:
            q &= Q(status=status)
        if start_time and end_time:
            q &= Q(created_at__range=[start_time, end_time])
        elif start_time:
            q &= Q(created_at__gte=start_time)
        elif end_time:
            q &= Q(created_at__lte=end_time)

        # 调用 Repository 层查询
        total, logs = await audit_log_repository.list_with_filter(
            page=page,
            page_size=page_size,
            search=q,
            order=["-created_at"]
        )

        return total, logs

    def _get_effective_tenant_id(self, request_tenant_id: int) -> int:
        """
        获取有效的租户ID

        - 超级管理员：使用请求中指定的租户ID
        - 普通用户：使用JWT token中的当前租户ID

        Args:
            request_tenant_id: 请求中指定的租户ID

        Returns:
            int: 有效的租户ID
        """
        current_user = Ctx.get_user()
        if is_superuser(current_user):
            return request_tenant_id if request_tenant_id is not None else 0
        else:
            return current_user.current_tenant_id if current_user else 0


# 全局 Service 实例
audit_log_service = AuditLogService()
