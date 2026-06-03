from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.ctx import Ctx
from app.core.dependency import AuthControl
from app.models.admin import User
from app.schemas.base import Fail, Success
from app.schemas.login import *
from app.schemas.users import UpdatePassword, UserTenantSelect
from app.services.system.api_service import api_service
from app.services.system.menu_service import menu_service
from app.services.system.tenant_service import tenant_service
from app.services.system.user_service import user_service
from app.settings import settings
from app.utils.jwt_utils import create_access_token

router = APIRouter()


@router.post("/access_token", summary="获取token")
async def login_access_token(credentials: CredentialsSchema):
    user: User = await user_service.authenticate(
        username=credentials.username,
        password=credentials.password
    )
    await user_service.update_last_login(user.id)

    current_tenant_id = user.current_tenant_id

    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + access_token_expires

    data = JWTOut(
        access_token=create_access_token(
            data=JWTPayload(
                user_id=user.id,
                username=user.username,
                is_superuser=user.is_superuser,
                exp=expire,
                current_tenant_id=current_tenant_id,
                tenant_domain="",
            )
        ),
        username=user.username,
        current_tenant_id=current_tenant_id,
    )
    return Success(data=data.model_dump())


@router.get("/userinfo", summary="查看用户信息")
async def get_userinfo(current_user: User = Depends(AuthControl.is_authed)):
    user_id = current_user.id
    user_obj = await user_service.get_user_by_id(user_id)
    data = await user_obj.to_dict(exclude_fields=["password"])

    # 添加当前租户ID
    data["current_tenant_id"] = user_obj.current_tenant_id

    return Success(data=data)


@router.get("/usermenu", summary="查看用户菜单")
async def get_user_menu(current_user: User = Depends(AuthControl.is_authed)):
    menus = await menu_service.get_user_menus(current_user.id, current_user.is_superuser)
    return Success(data=menus)


@router.get("/userapi", summary="查看用户API")
async def get_user_api():
    apis = await api_service.get_user_apis()
    return Success(data=apis)


@router.post("/update_password", summary="修改密码")
async def update_user_password(
    req_in: UpdatePassword,
    current_user: User = Depends(AuthControl.is_authed),
):
    await user_service.update_password(
        user_id=current_user.id,
        old_password=req_in.old_password,
        new_password=req_in.new_password
    )
    return Success(msg="密码修改成功")


@router.get("/select", summary="租户下拉选择")
async def tenant_select(keyword: str = Query("", description="搜索关键词（名称或域名）")):
    """
    租户下拉选择

    获取租户下拉列表，用于选择框
    - 超管可以搜索所有租户，支持清空（不传keyword返回全部）
    - 支持模糊搜索
    """
    try:
        # 超管可以查看所有租户
        if Ctx.is_superuser():
            tenants = await tenant_service.get_tenant_select_list(keyword)
        else:
            # 普通用户只能看到自己有权限的租户
            current_user = Ctx.get_user()
            tenant_list = await user_service.get_user_tenants(current_user.id)
            tenants = [{"id": t.id, "name": t.name, "domain": t.domain} for t in tenant_list if t.is_active]

            # 普通用户也支持模糊搜索
            if keyword:
                keyword_lower = keyword.lower()
                tenants = [
                    t for t in tenants
                    if keyword_lower in t["name"].lower() or keyword_lower in t["domain"].lower()
                ]

        return Success(data=tenants)
    except Exception as e:
        return Fail(code=400, msg=str(e))


@router.post("/select_tenant", summary="选择当前租户")
async def select_tenant(
    tenant_data: UserTenantSelect,
    current_user: User = Depends(AuthControl.is_authed),
):
    """
    用户选择当前操作的租户
    """
    try:
        await user_service.set_current_tenant(current_user.id, tenant_data.tenant_id)
        return Success(msg="租户选择成功")
    except Exception as e:
        return Fail(code=400, msg=str(e))


class QuickLoginSchema(BaseModel):
    target_user_id: int


@router.post("/quick_login", summary="快捷登录到其他用户")
async def quick_login(
    schema: QuickLoginSchema,
    current_user: User = Depends(AuthControl.is_authed),
):
    """快捷登录功能：允许具有权限的用户快速切换到其他用户
    - 需要用户具有 'post/api/v1/base/quick_login' 权限
    - 不能快捷登录到超级管理员
    - 如果目标用户有多个租户，需要选择租户
    """
    target_user = await user_service.quick_login_validate(
        current_user.id,
        schema.target_user_id,
        current_user.is_superuser
    )

    await user_service.update_last_login(target_user.id)

    current_tenant_id = target_user.current_tenant_id

    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + access_token_expires

    data = JWTOut(
        access_token=create_access_token(
            data=JWTPayload(
                user_id=target_user.id,
                username=target_user.username,
                is_superuser=target_user.is_superuser,
                exp=expire,
                current_tenant_id=current_tenant_id,
                tenant_domain="",
            )
        ),
        username=target_user.username,
        current_tenant_id=current_tenant_id,
    )
    return Success(data=data.model_dump())
