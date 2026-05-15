"""
填单记录管理接口
"""
from fastapi import APIRouter, Header, Query
from tortoise.expressions import Q

from app.controllers.autofill import fill_data_record_controller
from app.core.dependency import AuthControl, is_superuser, build_tenant_query, TenantControl
from app.schemas.autofill import FillDataRecordUpdate
from app.schemas.base import Fail, Success, SuccessExtra

router = APIRouter()


@router.get("/record/list", summary="填单记录列表")
async def list_record(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    session_id: str = Query("", description="会话ID"),
    phone: str = Query("", description="手机号"),
    user_unique_id: str = Query("", description="用户唯一标识"),
    app_name: str = Query("", description="应用名称"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    q = Q()
    if session_id:
        q &= Q(session_id__contains=session_id)
    if phone:
        q &= Q(phone__contains=phone)
    if user_unique_id:
        q &= Q(user_unique_id__contains=user_unique_id)
    if app_name:
        q &= Q(app_name__contains=app_name)

    tenant_query = build_tenant_query(current_user, tenant_id)
    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])

    total, records = await fill_data_record_controller.list(
        page=page, page_size=page_size, search=q, order=["-updated_at"]
    )
    data = [await obj.to_dict() for obj in records]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/record/get", summary="填单记录详情")
async def get_record(
    id: int = Query(..., description="记录ID"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    record = await fill_data_record_controller.get(id=id)
    return Success(data=await record.to_dict())


@router.post("/record/update", summary="更新填单记录")
async def update_record(
    record_in: FillDataRecordUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    record = await fill_data_record_controller.get(id=record_in.id)

    # 使用公共方法验证更新权限
    success, msg = TenantControl.validate_update_permission(
        current_user, record.tenant_id
    )
    if not success:
        return Fail(code=403, msg=msg)

    updated = await fill_data_record_controller.update(id=record_in.id, obj_in=record_in)
    return Success(data=await updated.to_dict())


@router.delete("/record/delete", summary="删除填单记录")
async def delete_record(
    id: int = Query(..., description="记录ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    record = await fill_data_record_controller.get(id=id)

    # 使用公共方法验证删除权限
    success, msg = TenantControl.validate_delete_permission(
        current_user, record.tenant_id
    )
    if not success:
        return Fail(code=403, msg=msg)

    await fill_data_record_controller.remove(id=id)
    return Success(msg="删除成功")
