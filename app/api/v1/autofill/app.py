"""
应用管理接口

参考 depts.py 简洁风格：
- 直接在路由函数中调用 Service 层
- 不使用 API 类包装
- 认证由中间件统一处理
- 租户过滤由 Repository 层自动处理
"""
from fastapi import APIRouter, Depends, Query

from app.schemas.autofill import AppCreate, AppUpdate, AppListQuery
from app.schemas.base import Fail, Success, SuccessExtra
from app.services.autofill.app_service import app_service

router = APIRouter()


@router.get("/app/list", summary="应用列表")
async def list_app(
    query: AppListQuery = Depends(),
):
    """获取应用列表"""
    total, apps = await app_service.list_apps(
        app_name=query.app_name,
        page=query.page,
        page_size=query.page_size
    )
    data = [await obj.to_dict() for obj in apps]
    return SuccessExtra(
        data=data,
        total=total,
        page=query.page,
        page_size=query.page_size
    )


@router.get("/app/get", summary="应用详情")
async def get_app(
    id: int = Query(..., description="应用ID"),
):
    """获取应用详情"""
    app = await app_service.get_app_by_id(app_id=id)
    if not app:
        return Fail(code=404, msg="应用不存在")
    return Success(data=await app.to_dict())


@router.post("/app/create", summary="创建应用")
async def create_app(
    app_in: AppCreate,
):
    """创建应用

    租户ID由 Repository 层自动从上下文获取并注入
    """
    try:
        app = await app_service.create_app(app_in=app_in)
        return Success(data=await app.to_dict())
    except Exception as e:
        return Fail(code=400, msg=str(e))


@router.post("/app/update", summary="更新应用")
async def update_app(
    app_in: AppUpdate,
):
    """更新应用信息"""
    try:
        updated = await app_service.update_app(
            app_id=app_in.id,
            app_in=app_in
        )
        return Success(data=await updated.to_dict())
    except Exception as e:
        return Fail(code=400, msg=str(e))


@router.delete("/app/delete", summary="删除应用")
async def delete_app(
    id: int = Query(..., description="应用ID"),
):
    """删除应用"""
    try:
        await app_service.delete_app(app_id=id)
        return Success(msg="删除成功")
    except Exception as e:
        return Fail(code=400, msg=str(e))


@router.get("/app/select", summary="应用名称下拉列表")
async def get_app_select():
    """获取应用下拉列表"""
    apps = await app_service.get_active_apps()
    data = [{"label": app.app_name, "value": app.app_name} for app in apps]
    return Success(data=data)
