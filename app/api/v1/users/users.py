import logging

from fastapi import APIRouter, Body, Header, Query
from tortoise.expressions import Q

from app.controllers.dept import dept_controller
from app.controllers.role import role_controller
from app.controllers.user import user_controller
from app.core.dependency import AuthControl
from app.core.relation import RelationQuery
from app.models.admin import Role, Tenant, User, UserTenant
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
            from app.models.admin import DeptClosure
            descendant_ids = await DeptClosure.filter(ancestor=dept_id).values_list("descendant", flat=True)
            if descendant_ids:
                q &= Q(dept_id__in=descendant_ids)
            else:
                q &= Q(dept_id=dept_id)
        else:
            q &= Q(dept_id=dept_id)

    # 多租户筛选：仅超级管理员可按租户筛选
    if tenant_id is not None and is_superuser(current_user):
        tenant_user_ids = await RelationQuery.get_user_ids_by_tenant_id(tenant_id)
        q &= Q(id__in=tenant_user_ids)
    elif not is_superuser(current_user):
        if current_user.current_tenant_id:
            tenant_user_ids = await RelationQuery.get_user_ids_by_tenant_id(current_user.current_tenant_id)
            q &= Q(id__in=tenant_user_ids)

    total, user_objs = await user_controller.list(page=page, page_size=page_size, search=q)
    data = [await obj.to_dict(exclude_fields=["password"]) for obj in user_objs]

    # 批量获取租户信息（仅超级管理员可见）
    if is_superuser(current_user):
        user_ids = [item["id"] for item in data]
        user_tenant_map = await RelationQuery.batch_get_tenant_ids_by_user_ids(user_ids)
        all_tenant_ids = set()
        for tids in user_tenant_map.values():
            all_tenant_ids.update(tids)
        tenant_map = {}
        if all_tenant_ids:
            tenants = await Tenant.filter(id__in=all_tenant_ids).all()
            tenant_map = {t.id: {"id": t.id, "name": t.name} for t in tenants}

        for item in data:
            item["tenants"] = [tenant_map.get(tid) for tid in user_tenant_map.get(item["id"], []) if tenant_map.get(tid)]

    for item in data:
        dept_id = item.pop("dept_id", None)
        item["dept"] = await (await dept_controller.get(id=dept_id)).to_dict() if dept_id else {}

    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/get", summary="查看用户")
async def get_user(
    user_id: int = Query(..., description="用户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    user_obj = await user_controller.get(id=user_id)
    user_dict = await user_obj.to_dict(exclude_fields=["password"])

    if is_superuser(current_user):
        tenant_ids = await RelationQuery.get_tenant_ids_by_user_id(user_id)
        user_dict["tenant_ids"] = tenant_ids

    return Success(data=user_dict)


@router.post("/create", summary="创建用户")
async def create_user(
    user_in: UserCreate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    if user_in.tenant_ids and not is_superuser(current_user):
        return Fail(code=403, msg="只有超级管理员才能指定租户")

    # 普通用户（非超级管理员）从JWT获取租户ID
    if not is_superuser(current_user):
        import jwt
        from app.settings import settings
        decode_data = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.JWT_ALGORITHM)
        current_tenant_id = decode_data.get("current_tenant_id")
        if current_tenant_id:
            user_in.tenant_ids = [current_tenant_id]
        else:
            return Fail(code=400, msg="您当前未选择租户，无法创建用户")

    user = await user_controller.get_by_email(user_in.email)
    if user:
        return Fail(code=400, msg="该邮箱已被注册")

    await user_controller.create_user(obj_in=user_in)

    return Success(msg="创建成功")


@router.post("/update", summary="更新用户")
async def update_user(
    user_in: UserUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    if user_in.tenant_ids and not is_superuser(current_user):
        return Fail(code=403, msg="只有超级管理员才能修改租户")

    await user_controller.update(id=user_in.id, obj_in=user_in)

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
        user_tenant_ids = await RelationQuery.get_tenant_ids_by_user_id(current_user.id)
        if tenant_id not in user_tenant_ids:
            return Fail(code=403, msg="您没有该租户的权限")

    roles = await role_controller.get_by_tenant(tenant_id)
    data = [await role.to_dict() for role in roles]
    return Success(data=data)


@router.get("/tenant_assigned_roles", summary="获取用户在指定租户下已分配的角色")
async def get_user_tenant_assigned_roles(
    user_id: int = Query(..., description="用户ID"),
    tenant_id: int = Query(..., description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """获取用户在指定租户下已分配的角色ID列表"""
    current_user = await AuthControl.is_authed(token)

    # 权限检查
    if not is_superuser(current_user):
        # 检查当前用户是否有权限查看该租户
        user_tenant_ids = await RelationQuery.get_tenant_ids_by_user_id(current_user.id)
        if tenant_id not in user_tenant_ids:
            return Fail(code=403, msg="您没有该租户的权限")

    # 获取用户的所有角色
    user_role_ids = await RelationQuery.get_role_ids_by_user_id(user_id)
    if not user_role_ids:
        return Success(data=[])

    # 筛选出属于该租户的角色
    roles = await Role.filter(id__in=user_role_ids).all()
    tenant_role_ids = [r.id for r in roles if r.tenant_id == tenant_id]

    return Success(data=tenant_role_ids)


@router.post("/update_tenant_roles", summary="更新用户在指定租户下的角色")
async def update_user_tenant_roles(
    data: UserUpdateTenantRoles,
    token: str = Header(..., description="token验证"),
):
    """更新用户在指定租户下的角色分配
    - 先删除用户在该租户下的所有角色关联
    - 然后添加新的角色关联
    - 如果用户不在该租户下，将用户添加到该租户
    """
    current_user = await AuthControl.is_authed(token)

    # 权限检查
    if not is_superuser(current_user):
        # 检查当前用户是否有权限操作该租户
        user_tenant_ids = await RelationQuery.get_tenant_ids_by_user_id(current_user.id)
        if data.tenant_id not in user_tenant_ids:
            return Fail(code=403, msg="您没有该租户的权限")

    # 获取用户当前的所有角色
    user_role_ids = await RelationQuery.get_role_ids_by_user_id(data.user_id)

    # 获取该租户下的所有角色
    tenant_roles = await role_controller.get_by_tenant(data.tenant_id)
    tenant_role_ids = {r.id for r in tenant_roles}

    # 保留不属于该租户的角色
    other_tenant_role_ids = []
    if user_role_ids:
        roles = await Role.filter(id__in=user_role_ids).all()
        other_tenant_role_ids = [r.id for r in roles if r.tenant_id != data.tenant_id]

    # 合并角色：其他租户的角色 + 新分配的角色
    final_role_ids = other_tenant_role_ids + data.role_ids

    # 更新用户角色关联
    await RelationQuery.replace_user_roles(data.user_id, final_role_ids)

    # 如果用户不在该租户下，将用户添加到该租户
    user_tenant_ids = await RelationQuery.get_tenant_ids_by_user_id(data.user_id)
    if data.tenant_id not in user_tenant_ids:
        await UserTenant.create(user_id=data.user_id, tenant_id=data.tenant_id)

    return Success(msg="更新成功")
