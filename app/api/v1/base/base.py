from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.dependency import AuthControl
from app.models.admin import User
from app.schemas.base import Fail, Success
from app.schemas.login import *
from app.schemas.users import UpdatePassword
from app.services.system.api_service import api_service
from app.services.system.menu_service import menu_service
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


class SelectTenantSchema(BaseModel):
    tenant_id: int

@router.post("/select_tenant", summary="选择租户后获取完整token")
async def select_tenant_and_get_token(
    schema: SelectTenantSchema,
    current_user: User = Depends(AuthControl.is_authed),
):
    """用户选择租户后，更新当前租户并返回新的token"""
    try:
        tenant_result = await user_service.select_tenant(current_user.id, schema.tenant_id)
        tenant_domain = tenant_result["tenant_domain"]

        access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.now(timezone.utc) + access_token_expires

        data = JWTOut(
            access_token=create_access_token(
                data=JWTPayload(
                    user_id=current_user.id,
                    username=current_user.username,
                    is_superuser=current_user.is_superuser,
                    exp=expire,
                    current_tenant_id=schema.tenant_id,
                    tenant_domain=tenant_domain,
                )
            ),
            username=current_user.username,
            current_tenant_id=schema.tenant_id,
        )
        return Success(data=data.model_dump())
    except Exception as e:
        return Fail(code=400, msg=str(e))


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
async def get_user_api(current_user: User = Depends(AuthControl.is_authed)):
    apis = await api_service.get_user_apis(current_user.id, current_user.is_superuser)
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
