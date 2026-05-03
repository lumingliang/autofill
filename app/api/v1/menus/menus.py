from fastapi import APIRouter, Header, Query

from app.controllers.menu import menu_controller
from app.core.dependency import AuthControl
from app.core.relation import RelationQuery
from app.log import logger
from app.models.admin import Menu, Role, User
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.menus import *
router = APIRouter()


@router.get("/list", summary="查看菜单列表")
async def list_menu(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    token: str = Header(..., description="token验证"),
):
    """获取菜单列表
    - 超级管理员：返回所有菜单
    - 普通用户：返回该用户有权限的菜单（用于角色权限分配）
    """
    current_user: User = await AuthControl.is_authed(token)

    # 获取用户有权限的菜单ID集合
    allowed_menu_ids = set()
    if current_user.is_superuser:
        all_menus = await Menu.all()
        allowed_menu_ids = {m.id for m in all_menus}
    else:
        # 通过RelationQuery批量获取菜单权限
        role_ids = await RelationQuery.get_role_ids_by_user_id(current_user.id)
        if role_ids:
            roles = await Role.filter(id__in=role_ids).all()
            target_role_ids = [
                r.id for r in roles
                if current_user.current_tenant_id and r.tenant_id == current_user.current_tenant_id
            ]
            if target_role_ids:
                menu_rows = await RelationQuery.batch_get_menu_ids_by_role_ids(target_role_ids)
                for mids in menu_rows.values():
                    allowed_menu_ids.update(mids)

    async def get_menu_with_children(menu_id: int):
        menu = await menu_controller.model.get(id=menu_id)
        menu_dict = await menu.to_dict()
        child_menus = await menu_controller.model.filter(parent_id=menu_id).order_by("order")
        menu_dict["children"] = []
        for child in child_menus:
            if child.id in allowed_menu_ids:
                menu_dict["children"].append(await get_menu_with_children(child.id))
        return menu_dict

    parent_menus = await menu_controller.model.filter(parent_id=0).order_by("order")
    res_menu = []
    for menu in parent_menus:
        if menu.id in allowed_menu_ids:
            res_menu.append(await get_menu_with_children(menu.id))

    return SuccessExtra(data=res_menu, total=len(res_menu), page=page, page_size=page_size)


@router.get("/get", summary="查看菜单")
async def get_menu(
    menu_id: int = Query(..., description="菜单id"),
):
    result = await menu_controller.get(id=menu_id)
    return Success(data=result)


@router.post("/create", summary="创建菜单")
async def create_menu(
    menu_in: MenuCreate,
):
    await menu_controller.create(obj_in=menu_in)
    return Success(msg="Created Success")


@router.post("/update", summary="更新菜单")
async def update_menu(
    menu_in: MenuUpdate,
):
    await menu_controller.update(id=menu_in.id, obj_in=menu_in)
    return Success(msg="Updated Success")


@router.delete("/delete", summary="删除菜单")
async def delete_menu(
    id: int = Query(..., description="菜单id"),
):
    child_menu_count = await menu_controller.model.filter(parent_id=id).count()
    if child_menu_count > 0:
        return Fail(msg="Cannot delete a menu with child menus")
    await menu_controller.remove(id=id)
    return Success(msg="Deleted Success")
