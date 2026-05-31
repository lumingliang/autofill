from fastapi import APIRouter, Depends

from app.services.system.role_service import role_service
from app.schemas.base import Success, SuccessExtra
from app.schemas.roles import (
    RoleCreate,
    RoleUpdate,
    RoleUpdateMenusApis,
    RoleAssignUsers,
    RoleListQuery,
    RoleGetQuery,
    RoleDeleteQuery,
    RoleAuthorizedQuery,
    RoleUsersQuery,
    RoleAvailableUsersQuery,
)

router = APIRouter()


@router.get("/list", summary="查看角色列表")
async def list_role(
    query: RoleListQuery = Depends(),
):
    total, role_objs = await role_service.list_roles(
        page=query.page,
        page_size=query.page_size,
        role_name=query.role_name
    )

    data = [await obj.to_dict() for obj in role_objs]

    return SuccessExtra(data=data, total=total, page=query.page, page_size=query.page_size)


@router.get("/get", summary="查看角色")
async def get_role(
    query: RoleGetQuery = Depends(),
):
    role_obj = await role_service.get_role_by_id(query.role_id)
    role_dict = await role_obj.to_dict()
    return Success(data=role_dict)


@router.post("/create", summary="创建角色")
async def create_role(
    role_in: RoleCreate,
):
    role = await role_service.create_role(role_in=role_in)
    return Success(msg="创建成功")


@router.post("/update", summary="更新角色")
async def update_role(
    role_in: RoleUpdate,
):
    await role_service.update_role(role_in=role_in)
    return Success(msg="更新成功")


@router.delete("/delete", summary="删除角色")
async def delete_role(
    query: RoleDeleteQuery = Depends(),
):
    await role_service.delete_role(role_id=query.role_id)
    return Success(msg="删除成功")


@router.get("/authorized", summary="查看角色权限")
async def get_role_authorized(
    query: RoleAuthorizedQuery = Depends(),
):
    role_obj = await role_service.get_role_by_id(query.id)
    role_dict = await role_obj.to_dict()
    menu_dicts, api_dicts = await role_service.get_role_permissions(query.id)

    role_dict["menus"] = menu_dicts
    role_dict["apis"] = api_dicts
    return Success(data=role_dict)


@router.post("/authorized", summary="更新角色权限")
async def update_role_authorized(
    role_in: RoleUpdateMenusApis,
):
    await role_service.update_role_permissions(
        role_id=role_in.id,
        menu_ids=role_in.menu_ids,
        api_codes=role_in.api_codes
    )
    return Success(msg="更新成功")


@router.get("/users", summary="获取角色已分配的用户")
async def get_role_users(
    query: RoleUsersQuery = Depends(),
):
    user_ids = await role_service.get_role_user_ids(query.role_id)
    return Success(data=user_ids)


@router.get("/available_users", summary="获取可分配给角色的用户列表")
async def get_available_users_for_role(
    query: RoleAvailableUsersQuery = Depends(),
):
    total, data = await role_service.get_available_users_for_role(
        role_id=query.role_id,
        page=query.page,
        page_size=query.page_size,
        username=query.username
    )
    return SuccessExtra(data=data, total=total, page=query.page, page_size=query.page_size)


@router.post("/assign_users", summary="分配用户给角色")
async def assign_users_to_role(
    data: RoleAssignUsers,
):
    await role_service.assign_users_to_role(
        role_id=data.role_id,
        user_ids=data.user_ids
    )
    return Success(msg="分配成功")
