from fastapi import APIRouter, Header, Query
from tortoise.expressions import Q

from app.controllers.api import api_controller
from app.core.dependency import AuthControl
from app.models.admin import Api, Role, User
from app.schemas import Success, SuccessExtra
from app.schemas.apis import *

router = APIRouter()


@router.get("/list", summary="查看API列表")
async def list_api(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    path: str = Query(None, description="API路径"),
    summary: str = Query(None, description="API简介"),
    tags: str = Query(None, description="API模块"),
    token: str = Header(..., description="token验证"),
):
    """获取API列表
    - 超级管理员：返回所有API
    - 普通用户：返回该用户有权限的API（用于角色权限分配）
    """
    current_user: User = await AuthControl.is_authed(token)

    q = Q()
    if path:
        q &= Q(path__contains=path)
    if summary:
        q &= Q(summary__contains=summary)
    if tags:
        q &= Q(tags__contains=tags)

    # 获取用户有权限的API ID集合
    allowed_api_ids = set()
    if current_user.is_superuser:
        # 超级管理员拥有所有API权限
        all_apis = await Api.all()
        allowed_api_ids = {a.id for a in all_apis}
    else:
        # 普通用户只能看到自己有权限的API
        role_objs: list[Role] = await current_user.roles
        for role_obj in role_objs:
            # 只获取当前租户的角色对应的API
            if current_user.current_tenant_id and role_obj.tenant_id == current_user.current_tenant_id:
                apis = await role_obj.apis
                for api in apis:
                    allowed_api_ids.add(api.id)

        # 如果没有权限，返回空列表
        if not allowed_api_ids:
            return SuccessExtra(data=[], total=0, page=page, page_size=page_size)

        # 添加API ID过滤条件
        q &= Q(id__in=allowed_api_ids)

    total, api_objs = await api_controller.list(page=page, page_size=page_size, search=q, order=["tags", "id"])
    data = [await obj.to_dict() for obj in api_objs]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/get", summary="查看Api")
async def get_api(
    id: int = Query(..., description="Api"),
):
    api_obj = await api_controller.get(id=id)
    data = await api_obj.to_dict()
    return Success(data=data)


@router.post("/create", summary="创建Api")
async def create_api(
    api_in: ApiCreate,
):
    await api_controller.create(obj_in=api_in)
    return Success(msg="Created Successfully")


@router.post("/update", summary="更新Api")
async def update_api(
    api_in: ApiUpdate,
):
    await api_controller.update(id=api_in.id, obj_in=api_in)
    return Success(msg="Update Successfully")


@router.delete("/delete", summary="删除Api")
async def delete_api(
    api_id: int = Query(..., description="ApiID"),
):
    await api_controller.remove(id=api_id)
    return Success(msg="Deleted Success")


@router.post("/refresh", summary="刷新API列表")
async def refresh_api():
    await api_controller.refresh_api()
    return Success(msg="OK")
