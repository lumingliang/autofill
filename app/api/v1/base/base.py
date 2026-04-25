from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from app.controllers.user import user_controller
from app.core.ctx import CTX_USER_ID
from app.core.dependency import AuthControl
from app.models.admin import Api, Menu, Role, Tenant, User
from app.schemas.base import Fail, Success
from app.schemas.login import *
from app.schemas.users import UpdatePassword
from app.settings import settings
from app.utils.jwt_utils import create_access_token
from app.utils.password import get_password_hash, verify_password

router = APIRouter()


@router.post("/access_token", summary="获取token")
async def login_access_token(credentials: CredentialsSchema):
    user: User = await user_controller.authenticate(credentials)
    await user_controller.update_last_login(user.id)
    
    # 获取用户所属租户
    tenants = await user_controller.get_user_tenants(user.id)
    tenant_list = [{"id": t.id, "name": t.name, "domain": t.domain} for t in tenants]
    
    # 如果用户只有一个租户且没有设置当前租户，自动设置为当前租户
    current_tenant_id = user.current_tenant_id
    if len(tenant_list) == 1 and not current_tenant_id:
        current_tenant_id = tenant_list[0]["id"]
        await user_controller.set_current_tenant(user.id, current_tenant_id)
    
    # 如果用户有多个租户，需要选择租户后才能获取完整token
    # 这里返回一个临时token，用于租户选择
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + access_token_expires

    data = JWTOut(
        access_token=create_access_token(
            data=JWTPayload(
                user_id=user.id,
                username=user.username,
                is_superuser=user.is_superuser,
                exp=expire,
            )
        ),
        username=user.username,
        # 多租户字段
        tenants=tenant_list,
        need_select_tenant=len(tenant_list) > 1 and not user.is_superuser,
        current_tenant_id=current_tenant_id,
    )
    return Success(data=data.model_dump())


class SelectTenantSchema(BaseModel):
    tenant_id: int

@router.post("/select_tenant", summary="选择租户后获取完整token")
async def select_tenant_and_get_token(
    schema: SelectTenantSchema,
    token: str = Header(..., description="token验证"),
):
    """用户选择租户后，更新当前租户并返回新的token"""
    try:
        # 验证token并获取用户
        current_user = await AuthControl.is_authed(token)
        await user_controller.set_current_tenant(current_user.id, schema.tenant_id)
        
        # 重新生成token
        access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.now(timezone.utc) + access_token_expires
        
        data = JWTOut(
            access_token=create_access_token(
                data=JWTPayload(
                    user_id=current_user.id,
                    username=current_user.username,
                    is_superuser=current_user.is_superuser,
                    exp=expire,
                )
            ),
            username=current_user.username,
            current_tenant_id=schema.tenant_id,
        )
        return Success(data=data.model_dump())
    except Exception as e:
        return Fail(code=400, msg=str(e))


@router.get("/userinfo", summary="查看用户信息")
async def get_userinfo(token: str = Header(..., description="token验证")):
    user = await AuthControl.is_authed(token)
    user_id = user.id
    user_obj = await user_controller.get(id=user_id)
    data = await user_obj.to_dict(exclude_fields=["password"])
    data["avatar"] = "https://avatars.githubusercontent.com/u/54677442?v=4"
    
    # 添加租户信息
    tenants = await user_controller.get_user_tenants(user_id)
    data["tenants"] = [{"id": t.id, "name": t.name, "domain": t.domain} for t in tenants]
    data["current_tenant_id"] = user_obj.current_tenant_id
    
    return Success(data=data)


@router.get("/usermenu", summary="查看用户菜单")
async def get_user_menu(token: str = Header(..., description="token验证")):
    user_obj = await AuthControl.is_authed(token)
    user_id = user_obj.id
    menus: list[Menu] = []
    
    if user_obj.is_superuser:
        menus = await Menu.all()
    else:
        # 如果没有当前租户，获取用户的第一个租户
        current_tenant_id = user_obj.current_tenant_id
        if not current_tenant_id:
            user_tenants = await user_controller.get_user_tenants(user_id)
            if user_tenants:
                current_tenant_id = user_tenants[0].id
                # 更新用户的当前租户
                await user_controller.set_current_tenant(user_id, current_tenant_id)
        
        role_objs: list[Role] = await user_obj.roles
        for role_obj in role_objs:
            # 多租户：只获取当前租户的角色对应的菜单
            if current_tenant_id and role_obj.tenant_id == current_tenant_id:
                menu = await role_obj.menus
                menus.extend(menu)
        menus = list(set(menus))
    
    parent_menus: list[Menu] = []
    for menu in menus:
        if menu.parent_id == 0:
            parent_menus.append(menu)
    res = []
    for parent_menu in parent_menus:
        parent_menu_dict = await parent_menu.to_dict()
        parent_menu_dict["children"] = []
        for menu in menus:
            if menu.parent_id == parent_menu.id:
                parent_menu_dict["children"].append(await menu.to_dict())
        res.append(parent_menu_dict)
    return Success(data=res)


@router.get("/userapi", summary="查看用户API")
async def get_user_api(token: str = Header(..., description="token验证")):
    user_obj = await AuthControl.is_authed(token)
    user_id = user_obj.id
    
    if user_obj.is_superuser:
        api_objs: list[Api] = await Api.all()
        apis = [api.method.lower() + api.path for api in api_objs]
        return Success(data=apis)
    
    # 如果没有当前租户，获取用户的第一个租户
    current_tenant_id = user_obj.current_tenant_id
    if not current_tenant_id:
        user_tenants = await user_controller.get_user_tenants(user_id)
        if user_tenants:
            current_tenant_id = user_tenants[0].id
            # 更新用户的当前租户
            await user_controller.set_current_tenant(user_id, current_tenant_id)
    
    role_objs: list[Role] = await user_obj.roles
    apis = []
    for role_obj in role_objs:
        # 多租户：只获取当前租户的角色对应的API
        if current_tenant_id and role_obj.tenant_id == current_tenant_id:
            api_objs: list[Api] = await role_obj.apis
            apis.extend([api.method.lower() + api.path for api in api_objs])
    apis = list(set(apis))
    return Success(data=apis)


@router.post("/update_password", summary="修改密码")
async def update_user_password(req_in: UpdatePassword, token: str = Header(..., description="token验证")):
    user = await AuthControl.is_authed(token)
    user_id = user.id
    user_obj = await user_controller.get(user_id)
    verified = verify_password(req_in.old_password, user_obj.password)
    if not verified:
        return Fail(msg="旧密码验证错误！")
    user_obj.password = get_password_hash(req_in.new_password)
    await user_obj.save()
    return Success(msg="密码修改成功")
