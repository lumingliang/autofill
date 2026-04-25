import logging

from fastapi import APIRouter, Header, Query
from fastapi.exceptions import HTTPException
from tortoise.expressions import Q

from app.controllers import role_controller
from app.controllers.user import user_controller
from app.core.dependency import AuthControl
from app.models.admin import User
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.roles import *

logger = logging.getLogger(__name__)
router = APIRouter()


def is_superuser(user: User) -> bool:
    """检查是否为超级管理员"""
    return user.is_superuser


@router.get("/list", summary="查看角色列表")
async def list_role(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    role_name: str = Query("", description="角色名称，用于查询"),
    tenant_id: int = Query(None, description="租户ID（仅root可见）"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    q = Q()
    if role_name:
        q &= Q(name__contains=role_name)
    
    # 多租户筛选
    if tenant_id is not None and is_superuser(current_user):
        # 超级管理员可按租户筛选
        q &= Q(tenant_id=tenant_id)
    elif not is_superuser(current_user):
        # 非超级管理员只能看到当前租户的角色
        if current_user.current_tenant_id:
            q &= Q(tenant_id=current_user.current_tenant_id)
        else:
            # 如果没有选择租户，只能看到系统级角色
            q &= Q(tenant_id=None)

    total, role_objs = await role_controller.list(page=page, page_size=page_size, search=q)
    data = []
    for obj in role_objs:
        role_dict = await obj.to_dict()
        # 添加租户名称（仅超级管理员可见）
        if is_superuser(current_user) and obj.tenant_id:
            from app.models.admin import Tenant
            tenant = await Tenant.filter(id=obj.tenant_id).first()
            role_dict["tenant_name"] = tenant.name if tenant else None
        data.append(role_dict)
    
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/get", summary="查看角色")
async def get_role(
    role_id: int = Query(..., description="角色ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    role_obj = await role_controller.get(id=role_id)
    role_dict = await role_obj.to_dict()

    # 添加租户信息（仅超级管理员可见）
    if is_superuser(current_user):
        role_dict["tenant_id"] = role_obj.tenant_id
        if role_obj.tenant_id:
            from app.models.admin import Tenant
            tenant = await Tenant.filter(id=role_obj.tenant_id).first()
            role_dict["tenant_name"] = tenant.name if tenant else None

    return Success(data=role_dict)


@router.post("/create", summary="创建角色")
async def create_role(
    role_in: RoleCreate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    # 检查权限：只有超级管理员可以创建带租户的角色
    if role_in.tenant_id and not is_superuser(current_user):
        return Fail(code=403, msg="只有超级管理员才能创建租户角色")

    # 非超级管理员创建的角色自动归属当前租户
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
    # 检查权限
    if role_in.tenant_id and not is_superuser(current_user):
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

    # 检查权限：非超级管理员不能删除系统角色
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

    # 检查权限：非超级管理员只能查看自己租户的角色
    if not is_superuser(current_user):
        if role_obj.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="您没有权限查看该角色")
    
    data = await role_obj.to_dict(m2m=True)
    return Success(data=data)


@router.post("/authorized", summary="更新角色权限")
async def update_role_authorized(
    role_in: RoleUpdateMenusApis,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    role_obj = await role_controller.get(id=role_in.id)

    # 检查权限：非超级管理员只能修改自己租户的角色
    if not is_superuser(current_user):
        if role_obj.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="您没有权限修改该角色")

        # 非超级管理员只能分配自己拥有的权限
        # 获取当前用户拥有的菜单权限
        user_role_objs: list[Role] = await current_user.roles
        allowed_menu_ids = set()
        allowed_api_paths = set()  # 存储 (path, method) 元组

        for user_role_obj in user_role_objs:
            # 只获取当前租户的角色对应的权限
            if current_user.current_tenant_id and user_role_obj.tenant_id == current_user.current_tenant_id:
                # 收集菜单权限
                menus = await user_role_obj.menus
                for menu in menus:
                    allowed_menu_ids.add(menu.id)
                # 收集API权限
                apis = await user_role_obj.apis
                for api in apis:
                    allowed_api_paths.add((api.path, api.method.lower()))

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
