from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Header, Query
from tortoise.expressions import Q

from app.core.dependency import AuthControl, is_superuser, get_effective_tenant_id
from app.repositories.system.audit_log_repository import audit_log_repository
from app.schemas import SuccessExtra
from app.schemas.apis import *

router = APIRouter()


@router.get("/list", summary="查看操作日志")
async def get_audit_log_list(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    username: str = Query("", description="操作人名称"),
    module: str = Query("", description="功能模块"),
    method: str = Query("", description="请求方法"),
    summary: str = Query("", description="接口描述"),
    path: str = Query("", description="请求路径"),
    status: int = Query(None, description="状态码"),
    tenant_id: int = Query(None, description="租户ID（仅超级管理员可见）"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
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

    # 多租户筛选：仅超级管理员可按租户筛选
    effective_tenant_id = get_effective_tenant_id(current_user, tenant_id if tenant_id is not None else 0)
    if effective_tenant_id > 0:
        q &= Q(tenant_id=effective_tenant_id)
    elif not is_superuser(current_user):
        # 非超级管理员且没有有效租户ID，使用当前租户ID（可能为0）
        q &= Q(tenant_id=current_user.current_tenant_id)

    total, audit_log_objs = await audit_log_repository.list_with_filter(
        page=page,
        page_size=page_size,
        search=q,
        order=["-created_at"]
    )
    data = [await audit_log.to_dict() for audit_log in audit_log_objs]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)
