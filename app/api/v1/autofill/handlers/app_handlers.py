"""
应用管理接口
"""
from fastapi import APIRouter, Header, Query
from tortoise.expressions import Q

from app.controllers.autofill import app_management_controller
from app.core.dependency import AuthControl, is_superuser, build_tenant_query, TenantControl
from app.schemas.autofill import AppCreate, AppUpdate
from app.schemas.base import Fail, Success, SuccessExtra

router = APIRouter()


@router.get("/app/list", summary="应用列表")
async def list_app(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    app_name: str = Query("", description="应用名称"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    q = Q()
    if app_name:
        q &= Q(app_name__contains=app_name)

    tenant_query = build_tenant_query(current_user, tenant_id)
    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])

    total, apps = await app_management_controller.list(
        page=page, page_size=page_size, search=q, order=["-updated_at"]
    )
    data = [await obj.to_dict() for obj in apps]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/app/get", summary="应用详情")
async def get_app(
    id: int = Query(..., description="应用ID"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    app = await app_management_controller.get(id=id)
    return Success(data=await app.to_dict())


@router.post("/app/create", summary="创建应用")
async def create_app(
    app_in: AppCreate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    # 使用公共方法验证租户ID
    success, msg, effective_tenant_id = TenantControl.validate_create_tenant_id(
        current_user, app_in.tenant_id
    )
    if not success:
        return Fail(code=400, msg=msg)
    app_in.tenant_id = effective_tenant_id

    app = await app_management_controller.create_app(obj_in=app_in)
    return Success(data=await app.to_dict())


@router.post("/app/update", summary="更新应用")
async def update_app(
    app_in: AppUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    app = await app_management_controller.get(id=app_in.id)

    if not is_superuser(current_user):
        if app.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的应用")

    updated = await app_management_controller.update_app(id=app_in.id, obj_in=app_in)
    return Success(data=await updated.to_dict())


@router.delete("/app/delete", summary="删除应用")
async def delete_app(
    id: int = Query(..., description="应用ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    app = await app_management_controller.get(id=id)

    # 使用公共方法验证删除权限
    success, msg = TenantControl.validate_delete_permission(
        current_user, app.tenant_id
    )
    if not success:
        return Fail(code=403, msg=msg)

    await app_management_controller.remove(id=id)
    return Success(msg="删除成功")


@router.get("/app/select", summary="应用名称下拉列表")
async def get_app_select(
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    q = Q(is_active=True)
    tenant_query = build_tenant_query(current_user, tenant_id)
    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])

    apps = await app_management_controller.model.filter(q).all()
    data = [{"label": app.app_name, "value": app.app_name} for app in apps]
    return Success(data=data)
