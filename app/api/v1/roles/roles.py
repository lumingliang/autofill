import logging

from fastapi import APIRouter, Header, Query
from fastapi.exceptions import HTTPException
from tortoise.expressions import Q

from app.controllers import role_controller
from app.controllers.user import user_controller
from app.core.dependency import AuthControl, is_superuser, build_tenant_query
from app.core.relation import RelationQuery
from app.models.admin import Api, Menu, Role, Tenant, User, UserRole, UserTenant
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.roles import *

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/list", summary="查看角色列表")
async def list_role(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    role_name: str = Query("", description="角色名称，用于查询"),
    tenant_id: int = Query(0, description="租户ID（仅root可见）"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    q = Q()
    if role_name:
        q &= Q(name__contains=role_name)

    # 多租户筛选
    tenant_query = build_tenant_query(current_user, tenant_id)
    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])
    elif not is_superuser(current_user) and current_user.current_tenant_id <= 0:
        q &= Q(tenant_id=0)

    total, role_objs = await role_controller.list(page=page, page_size=page_size, search=q, order=["-updated_at"])
    data = []
    tenant_ids = []
    for obj in role_objs:
        role_dict = await obj.to_dict()
        if is_superuser(current_user) and obj.tenant_id > 0:
            tenant_ids.append(obj.tenant_id)
        data.append(role_dict)

    # 批量查询租户名称
    if tenant_ids:
        tenants = await Tenant.filter(id__in=tenant_ids).all()
        tenant_map = {t.id: t.name for t in tenants}
        for role_dict, obj in zip(data, role_objs):
            if is_superuser(current_user) and obj.tenant_id:
                role_dict["tenant_name"] = tenant_map.get(obj.tenant_id)

    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/get", summary="查看角色")
async def get_role(
    role_id: int = Query(..., description="角色ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    role_obj = await role_controller.get(id=role_id)
    role_dict = await role_obj.to_dict()

    if is_superuser(current_user):
        role_dict["tenant_id"] = role_obj.tenant_id
        if role_obj.tenant_id > 0:
            tenant = await Tenant.filter(id=role_obj.tenant_id).first()
            role_dict["tenant_name"] = tenant.name if tenant else ""

    return Success(data=role_dict)


@router.post("/create", summary="创建角色")
async def create_role(
    role_in: RoleCreate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    if role_in.tenant_id > 0 and not is_superuser(current_user):
        return Fail(code=403, msg="只有超级管理员才能创建租户角色")

    if not is_superuser(current_user):
        role_in.tenant_id = current_user.current_tenant_id

    if await role_controller.is_exist(name=role_in.name, tenant_id=role_in.tenant_id):
        raise HTTPException(
            status_code=400,
            detail="该角色名称已存在",
        )
    await role_controller.create(obj_in=role_in)
    return Success(msg="创建成功")


@router.post("/update", summary="更新角色")
async def update_role(
    role_in: RoleUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    if role_in.tenant_id > 0 and not is_superuser(current_user):
        return Fail(code=403, msg="只有超级管理员才能修改租户")

    await role_controller.update(id=role_in.id, obj_in=role_in)
    return Success(msg="更新成功")


@router.delete("/delete", summary="删除角色")
async def delete_role(
    role_id: int = Query(..., description="角色ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    role_obj = await role_controller.get(id=role_id)

    if not is_superuser(current_user) and role_obj.is_system:
        return Fail(code=403, msg="不能删除系统角色")

    await role_controller.remove(id=role_id)
    return Success(msg="删除成功")


@router.get("/authorized", summary="查看角色权限")
async def get_role_authorized(
    id: int = Query(..., description="角色ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    role_obj = await role_controller.get(id=id)

    if not is_superuser(current_user):
        if role_obj.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="您没有权限查看该角色")

    role_dict = await role_obj.to_dict()
    # 通过RelationQuery获取关联的菜单和API
    menu_ids = await RelationQuery.get_menu_ids_by_role_id(role_obj.id)
    api_ids = await RelationQuery.get_api_ids_by_role_id(role_obj.id)

    menus = await Menu.filter(id__in=menu_ids).all()
    apis = await Api.filter(id__in=api_ids).all()

    role_dict["menus"] = [await m.to_dict() for m in menus]
    role_dict["apis"] = [await a.to_dict() for a in apis]
    return Success(data=role_dict)


@router.post("/authorized", summary="更新角色权限")
async def update_role_authorized(
    role_in: RoleUpdateMenusApis,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    role_obj = await role_controller.get(id=role_in.id)

    if not is_superuser(current_user):
        if role_obj.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="您没有权限修改该角色")

        # 非超级管理员只能分配自己拥有的权限
        # 获取当前用户拥有的角色ID
        user_role_ids = await RelationQuery.get_role_ids_by_user_id(current_user.id)
        if not user_role_ids:
            return Fail(code=403, msg="您没有权限分配权限")

        # 批量获取这些角色在当前租户下的菜单和API权限（使用表字段过滤）
        target_role_ids = await Role.filter(
            id__in=user_role_ids,
            tenant_id=current_user.current_tenant_id
        ).values_list("id", flat=True)

        allowed_menu_ids = set()
        allowed_api_paths = set()

        if target_role_ids:
            # 批量查询菜单权限
            menu_rows = await RelationQuery.batch_get_menu_ids_by_role_ids(target_role_ids)
            for mids in menu_rows.values():
                allowed_menu_ids.update(mids)

            # 批量查询API权限
            api_rows = await RelationQuery.batch_get_api_ids_by_role_ids(target_role_ids)
            all_api_ids = set()
            for aids in api_rows.values():
                all_api_ids.update(aids)

            if all_api_ids:
                api_objs = await Api.filter(id__in=all_api_ids).all()
                allowed_api_paths = {(a.path, a.method.lower()) for a in api_objs}

        # 验证要分配的菜单权限是否都在允许范围内
        for menu_id in role_in.menu_ids:
            if menu_id not in allowed_menu_ids:
                return Fail(code=403, msg=f"您没有权限分配菜单ID: {menu_id}")

        # 验证要分配的API权限是否都在允许范围内
        for api_info in role_in.api_infos:
            api_key = (api_info.get("path"), api_info.get("method", "").lower())
            if api_key not in allowed_api_paths:
                return Fail(code=403, msg=f"您没有权限分配API: {api_info.get('method')} {api_info.get('path')}")

    await role_controller.update_roles(role=role_obj, menu_ids=role_in.menu_ids, api_infos=role_in.api_infos)
    return Success(msg="更新成功")


@router.get("/users", summary="获取角色已分配的用户")
async def get_role_users(
    role_id: int = Query(..., description="角色ID"),
    token: str = Header(..., description="token验证"),
):
    """获取指定角色已分配的用户列表"""
    current_user = await AuthControl.is_authed(token)
    role_obj = await role_controller.get(id=role_id)

    # 权限检查
    if not is_superuser(current_user):
        if role_obj.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="您没有权限查看该角色")

    # 获取已分配的用户ID列表
    user_ids = await RelationQuery.get_user_ids_by_role_id(role_id)
    return Success(data=user_ids)


@router.get("/available_users", summary="获取可分配给角色的用户列表")
async def get_available_users_for_role(
    role_id: int = Query(..., description="角色ID"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    username: str = Query("", description="用户名搜索"),
    token: str = Header(..., description="token验证"),
):
    """
    获取可分配给角色的用户列表
    - 如果角色有租户ID，则返回该租户下的用户
    - 如果角色是系统角色（无租户），则返回所有用户（仅超级管理员）或当前租户下的用户
    """
    current_user = await AuthControl.is_authed(token)
    role_obj = await role_controller.get(id=role_id)

    # 权限检查
    if not is_superuser(current_user):
        if role_obj.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="您没有权限查看该角色")

    # 构建查询条件
    q = Q()
    if username:
        q &= Q(username__contains=username)

    # 根据角色的租户ID筛选用户
    if role_obj.tenant_id is not None:
        # 角色属于特定租户
        if not is_superuser(current_user):
            # 非超级管理员只返回该租户下的用户
            tenant_user_ids = await RelationQuery.get_user_ids_by_tenant_id(role_obj.tenant_id)
            q &= Q(id__in=tenant_user_ids)
        # 超级管理员可以查看所有用户，不做限制
    else:
        # 系统角色（无租户）
        if not is_superuser(current_user):
            # 非超级管理员只能看到当前租户下的用户
            if current_user.current_tenant_id:
                tenant_user_ids = await RelationQuery.get_user_ids_by_tenant_id(current_user.current_tenant_id)
                q &= Q(id__in=tenant_user_ids)

    total, user_objs = await user_controller.list(page=page, page_size=page_size, search=q)
    data = [await obj.to_dict(exclude_fields=["password"]) for obj in user_objs]

    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.post("/assign_users", summary="分配用户给角色")
async def assign_users_to_role(
    data: RoleAssignUsers,
    token: str = Header(..., description="token验证"),
):
    """为角色分配用户，同时将这些用户关联到角色对应的租户"""
    current_user = await AuthControl.is_authed(token)
    role_obj = await role_controller.get(id=data.role_id)

    # 权限检查
    if not is_superuser(current_user):
        if role_obj.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="您没有权限修改该角色")

    # 获取当前已分配的用户
    current_user_ids = set(await RelationQuery.get_user_ids_by_role_id(data.role_id))
    new_user_ids = set(data.user_ids)

    # 计算需要添加和删除的用户
    users_to_add = new_user_ids - current_user_ids
    users_to_remove = current_user_ids - new_user_ids

    # 获取角色对应的租户ID
    tenant_id = role_obj.tenant_id

    # 批量添加新的用户-角色关联
    if users_to_add:
        pairs = [(uid, data.role_id, tenant_id) for uid in users_to_add]
        await RelationQuery.batch_add_user_roles(pairs)

        # 如果有租户，将用户添加到租户
        if tenant_id:
            tenant_pairs = [(uid, tenant_id) for uid in users_to_add]
            await RelationQuery.batch_add_user_tenants(tenant_pairs)

    # 删除用户-角色关联
    if users_to_remove:
        for user_id in users_to_remove:
            await UserRole.filter(user_id=user_id, role_id=data.role_id).delete()

        # 如果有租户，检查这些用户是否还有其他角色在该租户下
        # 如果没有其他角色，则移除用户与租户的关联
        if tenant_id:
            for user_id in users_to_remove:
                # 获取用户在该租户下的其他角色（使用表字段过滤）
                user_role_ids = await RelationQuery.get_role_ids_by_user_id(user_id)
                if user_role_ids:
                    has_other_role_in_tenant = await Role.filter(
                        id__in=user_role_ids,
                        tenant_id=tenant_id
                    ).exists()
                    if not has_other_role_in_tenant:
                        await UserTenant.filter(user_id=user_id, tenant_id=tenant_id).delete()

    return Success(msg="分配成功")
