from fastapi import APIRouter, Depends

from app.core.dependency import AuthControl
from app.models.admin import User
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.menus import MenuCreate, MenuDeleteQuery, MenuGetQuery, MenuListQuery, MenuUpdate
from app.services.system.menu_service import menu_service

router = APIRouter()


@router.get("/list", summary="查看菜单列表")
async def list_menu(
    query: MenuListQuery = Depends(),
    user: User = Depends(AuthControl.is_authed),
):
    """获取菜单列表
    - 超级管理员：返回所有菜单
    - 普通用户：返回该用户有权限的菜单（用于角色权限分配）
    """
    total, data = await menu_service.list_with_permission(
        user_id=user.id,
        is_superuser=user.is_superuser,
        page=query.page,
        page_size=query.page_size
    )
    return SuccessExtra(data=data, total=total, page=query.page, page_size=query.page_size)


@router.get("/get", summary="查看菜单")
async def get_menu(
    query: MenuGetQuery = Depends(),
):
    result = await menu_service.get_by_id(query.menu_id)
    return Success(data=result)


@router.post("/create", summary="创建菜单")
async def create_menu(
    menu_in: MenuCreate,
):
    await menu_service.create(menu_in.model_dump())
    return Success(msg="Created Success")


@router.post("/update", summary="更新菜单")
async def update_menu(
    menu_in: MenuUpdate,
):
    await menu_service.update(menu_in.id, menu_in.model_dump(exclude={"id"}))
    return Success(msg="Updated Success")


@router.delete("/delete", summary="删除菜单")
async def delete_menu(
    query: MenuDeleteQuery = Depends(),
):
    try:
        await menu_service.delete(query.id)
        return Success(msg="Deleted Success")
    except ValueError as e:
        return Fail(msg=str(e))
