from fastapi import APIRouter, Body, Header, Query
from tortoise.expressions import Q

from app.controllers.tenant import tenant_controller
from app.core.dependency import AuthControl, is_superuser
from app.core.relation import RelationQuery
from app.log import logger
from app.models.admin import Tenant, User
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.tenants import TenantCreate, TenantUpdate
router = APIRouter()


@router.get("/list", summary="查看租户列表")
async def list_tenant(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    name: str = Query("", description="租户名称"),
    domain: str = Query("", description="租户域名"),
    token: str = Header(..., description="token验证"),
):
    """仅超级管理员可查看租户列表"""
    current_user = await AuthControl.is_authed(token)
    if not is_superuser(current_user):
        return Fail(code=403, msg="只有超级管理员才能管理租户")

    q = Q()
    if name:
        q &= Q(name__contains=name)
    if domain:
        q &= Q(domain__contains=domain)

    total, tenant_objs = await tenant_controller.list(page=page, page_size=page_size, search=q, order=["-updated_at"])
    data = [await obj.to_dict() for obj in tenant_objs]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/get", summary="查看租户")
async def get_tenant(
    tenant_id: int = Query(..., description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    if not is_superuser(current_user):
        return Fail(code=403, msg="只有超级管理员才能查看租户")

    tenant_obj = await tenant_controller.get(id=tenant_id)
    tenant_dict = await tenant_obj.to_dict()
    return Success(data=tenant_dict)


@router.post("/create", summary="创建租户")
async def create_tenant(
    tenant_in: TenantCreate,
    token: str = Header(..., description="token验证"),
):
    """仅超级管理员可创建租户，自动创建该租户的管理员角色"""
    current_user = await AuthControl.is_authed(token)
    if not is_superuser(current_user):
        return Fail(code=403, msg="只有超级管理员才能创建租户")

    try:
        tenant, admin_role = await tenant_controller.create_tenant(tenant_in)
        return Success(
            data={
                "tenant": await tenant.to_dict(),
                "admin_role_id": admin_role.id,
                "message": f"租户创建成功，已自动创建管理员角色：{admin_role.name}",
            },
            msg="创建成功",
        )
    except Exception as e:
        logger.error(f"创建租户失败: {e}")
        return Fail(code=400, msg=str(e))


@router.post("/update", summary="更新租户")
async def update_tenant(
    tenant_in: TenantUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    if not is_superuser(current_user):
        return Fail(code=403, msg="只有超级管理员才能更新租户")

    await tenant_controller.update(id=tenant_in.id, obj_in=tenant_in)
    return Success(msg="更新成功")


@router.delete("/delete", summary="删除租户")
async def delete_tenant(
    tenant_id: int = Query(..., description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    if not is_superuser(current_user):
        return Fail(code=403, msg="只有超级管理员才能删除租户")

    await tenant_controller.remove(id=tenant_id)
    return Success(msg="删除成功")


@router.get("/select", summary="租户下拉选择")
async def tenant_select(
    token: str = Header(..., description="token验证"),
):
    """获取租户下拉列表，用于选择框"""
    current_user = await AuthControl.is_authed(token)
    if is_superuser(current_user):
        # 超级管理员可以看到所有租户
        tenants = await Tenant.filter(is_active=True).all()
    else:
        # 普通用户只能看到自己有权限的租户
        tenant_ids = await RelationQuery.get_tenant_ids_by_user_id(current_user.id)
        if not tenant_ids:
            tenants = []
        else:
            tenants = await Tenant.filter(id__in=tenant_ids, is_active=True).all()

    data = [{"id": t.id, "name": t.name, "domain": t.domain} for t in tenants]
    return Success(data=data)


@router.get("/users", summary="获取租户下的用户")
async def get_tenant_users(
    tenant_id: int = Query(..., description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """获取指定租户下的所有用户"""
    current_user = await AuthControl.is_authed(token)
    if not is_superuser(current_user):
        return Fail(code=403, msg="只有超级管理员才能查看租户用户")

    users = await tenant_controller.get_tenant_users(tenant_id)
    data = [await user.to_dict(exclude_fields=["password"]) for user in users]
    return Success(data=data)


@router.post("/add_user", summary="添加用户到租户")
async def add_user_to_tenant(
    tenant_id: int = Body(..., description="租户ID"),
    user_id: int = Body(..., description="用户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    if not is_superuser(current_user):
        return Fail(code=403, msg="只有超级管理员才能管理租户用户")

    await tenant_controller.add_user_to_tenant(tenant_id, user_id)
    return Success(msg="添加成功")


@router.post("/remove_user", summary="从租户移除用户")
async def remove_user_from_tenant(
    tenant_id: int = Body(..., description="租户ID"),
    user_id: int = Body(..., description="用户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    if not is_superuser(current_user):
        return Fail(code=403, msg="只有超级管理员才能管理租户用户")

    await tenant_controller.remove_user_from_tenant(tenant_id, user_id)
    return Success(msg="移除成功")
