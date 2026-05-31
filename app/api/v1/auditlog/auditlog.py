"""
审计日志 API 层

接收 HTTP 请求，调用 Service 层处理业务逻辑

约束：
- 只负责接收请求、参数校验、调用 Service 层
- 禁止直接操作数据库、直接访问 Repository 层
- 禁止直接查询 Model 层
- 认证已在中间件处理，API层不再重复认证
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from app.core.ctx import Ctx
from app.schemas import SuccessExtra
from app.schemas.apis import *
from app.services.system.audit_log_service import audit_log_service

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
):
    """
    查看操作日志列表

    权限：所有登录用户可查看，租户过滤自动应用
    认证：已在中间件处理
    """
    # 从上下文获取当前用户
    current_user = await Ctx.get_current_user()

    # 调用 Service 层处理业务逻辑
    total, audit_log_objs = await audit_log_service.list_audit_logs(
        page=page,
        page_size=page_size,
        username=username,
        module=module,
        method=method,
        summary=summary,
        path=path,
        status=status,
        tenant_id=tenant_id,
        start_time=start_time,
        end_time=end_time,
        current_user=current_user
    )

    # 转换数据
    data = [await audit_log.to_dict() for audit_log in audit_log_objs]

    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)
