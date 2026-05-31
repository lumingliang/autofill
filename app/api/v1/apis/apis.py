from fastapi import APIRouter, Depends, Request

from app.core.dependency import AuthControl
from app.models.admin import User
from app.schemas import Success, SuccessExtra
from app.schemas.apis import ApiListQuery
from app.services.system.api_service import api_service

router = APIRouter()


@router.get("/list", summary="查看API列表")
async def list_api(
    query: ApiListQuery = Depends(),
    user: User = Depends(AuthControl.is_authed),
):
    """获取API列表
    - 超级管理员：返回所有API
    - 普通用户：返回该用户有权限的API（用于角色权限分配）
    """
    total, api_objs = await api_service.list_with_permission(
        api_code=query.api_code,
        path=query.path,
        summary=query.summary,
        tags=query.tags,
        page=query.page,
        page_size=query.page_size
    )

    data = [await obj.to_dict() for obj in api_objs]
    return SuccessExtra(data=data, total=total, page=query.page, page_size=query.page_size)


@router.post("/refresh", summary="刷新API列表")
async def refresh_api(request: Request):
    await api_service.refresh_api(request.app)
    return Success(msg="OK")
