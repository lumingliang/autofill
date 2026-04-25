import logging

from fastapi import APIRouter, Body, Header, Query
from tortoise.expressions import Q

from app.controllers.dept import dept_controller
from app.controllers.role import role_controller
from app.controllers.user import user_controller
from app.core.dependency import AuthControl
from app.models.admin import User
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.users import *

logger = logging.getLogger(__name__)

router = APIRouter()


def is_superuser(user: User) -> bool:
    """检查是否为超级管理员"""
    return user.is_superuser


@router.get("/list", summary="查看用户列表")
async def list_user(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    username: str = Query("", description="用户名称，用于搜索"),
    email: str = Query("", description="邮箱地址"),
    dept_id: int = Query(None, description="部门ID"),
    dept_recursive: bool = Query(True, description="是否递归查询子部门"),
    tenant_id: int = Query(None, description="租户ID（仅root可见）"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    q = Q()
    if username:
        q &= Q(username__contains=username)
    if email:
        q &= Q(email__contains=email)
    if dept_id is not None:
        if dept_recursive:
            # 递归查询该部门及其所有子部门下的用户
            from app.models.admin import Dept, DeptClosure
            # 获取该部门的所有后代部门ID
            descendant_ids = await DeptClosure.filter(ancestor=dept_id).values_list("descendant", flat=True)
            if descendant_ids:
                q &= Q(dept_id__in=descendant_ids)
            else:
                q &= Q(dept_id=dept_id)
        else:
            q &= Q(dept_id=dept_id)
    
    # 多租户筛选：仅超级管理员可按租户筛选
    if tenant_id is not None and is_superuser(current_user):
        # 获取该租户下的所有用户ID
        from app.models.admin import Tenant
        tenant = await Tenant.filter(id=tenant_id).first()
        if tenant:
            tenant_user_ids = [u.id for u in await tenant.tenant_users.all()]
            q &= Q(id__in=tenant_user_ids)
    elif not is_superuser(current_user):
        # 非超级管理员只能看到当前选中租户的数据
        if current_user.current_tenant_id:
            from app.models.admin import Tenant
            tenant = await Tenant.filter(id=current_user.current_tenant_id).first()
            if tenant:
                tenant_user_ids = [u.id for u in await tenant.tenant_users.all()]
                q &= Q(id__in=tenant_user_ids)

    total, user_objs = await user_controller.list(page=page, page_size=page_size, search=q)
    data = [await obj.to_dict(m2m=True, exclude_fields=["password"]) for obj in user_objs]
    for item in data:
        dept_id = item.pop("dept_id", None)
        item["dept"] = await (await dept_controller.get(id=dept_id)).to_dict() if dept_id else {}

        # 添加租户信息（仅超级管理员可见）
        if is_superuser(current_user):
            user_obj = await user_controller.get(id=item["id"])
            tenants = await user_obj.tenants.all()
            item["tenants"] = [{"id": t.id, "name": t.name} for t in tenants]

    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/get", summary="查看用户")
async def get_user(
    user_id: int = Query(..., description="用户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    user_obj = await user_controller.get(id=user_id)
    user_dict = await user_obj.to_dict(m2m=True, exclude_fields=["password"])

    # 添加租户信息（仅超级管理员可见）
    if is_superuser(current_user):
        tenants = await user_obj.tenants.all()
        user_dict["tenant_ids"] = [t.id for t in tenants]

    return Success(data=user_dict)


@router.post("/create", summary="创建用户")
async def create_user(
    user_in: UserCreate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    
    # 检查权限：只有超级管理员可以指定租户
    if user_in.tenant_ids and not is_superuser(current_user):
        return Fail(code=403, msg="只有超级管理员才能指定租户")
    
    # 非超级管理员创建的用户自动绑定当前租户
    if not is_superuser(current_user):
        if current_user.current_tenant_id:
            user_in.tenant_ids = [current_user.current_tenant_id]
        else:
            return Fail(code=400, msg="您当前未选择租户，无法创建用户")

    user = await user_controller.get_by_email(user_in.email)
    if user:
        return Fail(code=400, msg="该邮箱已被注册")
    
    new_user = await user_controller.create_user(obj_in=user_in)
    await user_controller.update_roles(new_user, user_in.role_ids)
    
    # 关联租户
    if user_in.tenant_ids:
        await user_controller.update_tenants(new_user, user_in.tenant_ids)
    
    return Success(msg="创建成功")


@router.post("/update", summary="更新用户")
async def update_user(
    user_in: UserUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    # 检查权限：只有超级管理员可以修改租户
    if user_in.tenant_ids and not is_superuser(current_user):
        return Fail(code=403, msg="只有超级管理员才能修改租户")

    user = await user_controller.update(id=user_in.id, obj_in=user_in)
    await user_controller.update_roles(user, user_in.role_ids)
    
    # 更新租户关联
    if user_in.tenant_ids:
        await user_controller.update_tenants(user, user_in.tenant_ids)
    
    return Success(msg="更新成功")


@router.delete("/delete", summary="删除用户")
async def delete_user(
    user_id: int = Query(..., description="用户ID"),
    token: str = Header(..., description="token验证"),
):
    await user_controller.remove(id=user_id)
    return Success(msg="删除成功")


@router.post("/reset_password", summary="重置密码")
async def reset_password(user_id: int = Body(..., description="用户ID", embed=True)):
    await user_controller.reset_password(user_id)
    return Success(msg="密码已重置为123456")


@router.get("/my_tenants", summary="获取我的租户列表")
async def get_my_tenants(
    token: str = Header(..., description="token验证"),
):
    """获取当前用户所属的所有租户"""
    current_user = await AuthControl.is_authed(token)
    tenants = await user_controller.get_user_tenants(current_user.id)
    data = [{"id": t.id, "name": t.name, "domain": t.domain} for t in tenants]
    return Success(data=data)


@router.post("/select_tenant", summary="选择当前租户")
async def select_tenant(
    tenant_data: UserTenantSelect,
    token: str = Header(..., description="token验证"),
):
    """用户选择当前操作的租户"""
    current_user = await AuthControl.is_authed(token)
    try:
        await user_controller.set_current_tenant(current_user.id, tenant_data.tenant_id)
        return Success(msg="租户选择成功")
    except Exception as e:
        return Fail(code=400, msg=str(e))


@router.get("/tenant_roles", summary="获取指定租户的角色")
async def get_tenant_roles(
    tenant_id: int = Query(..., description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """获取指定租户下的所有角色，用于给用户分配角色"""
    current_user = await AuthControl.is_authed(token)
    if not is_superuser(current_user):
        # 非超级管理员只能查看自己有权限的租户的角色
        user_tenants = await user_controller.get_user_tenants(current_user.id)
        tenant_ids = [t.id for t in user_tenants]
        if tenant_id not in tenant_ids:
            return Fail(code=403, msg="您没有该租户的权限")

    roles = await role_controller.get_by_tenant(tenant_id)
    data = [await role.to_dict() for role in roles]
    return Success(data=data)
