from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header
from pydantic import BaseModel

from app.controllers.user import user_controller
from app.core.dependency import AuthControl
from app.core.relation import RelationQuery
from app.models.admin import Api, Menu, Tenant, User
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
    tenant_domain = None
    if len(tenant_list) == 1 and not current_tenant_id:
        current_tenant_id = tenant_list[0]["id"]
        tenant_domain = tenant_list[0]["domain"]
        await user_controller.set_current_tenant(user.id, current_tenant_id)
    elif current_tenant_id:
        for t in tenant_list:
            if t["id"] == current_tenant_id:
                tenant_domain = t["domain"]
                break

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
                tenant_domain=tenant_domain,
            )
        ),
        username=user.username,
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
        current_user = await AuthControl.is_authed(token)
        await user_controller.set_current_tenant(current_user.id, schema.tenant_id)

        tenant = await Tenant.filter(id=schema.tenant_id).first()
        tenant_domain = tenant.domain if tenant else None

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
async def get_userinfo(token: str = Header(..., description="token验证")):
    user = await AuthControl.is_authed(token)
    user_id = user.id
    user_obj = await user_controller.get(id=user_id)
    data = await user_obj.to_dict(exclude_fields=["password"])
    if not data.get("avatar"):
        data["avatar"] = "https://avatars.githubusercontent.com/u/54677442?v=4"

    # 添加租户信息
    tenants = await user_controller.get_user_tenants(user_id)
    data["tenants"] = [{"id": t.id, "name": t.name, "domain": t.domain} for t in tenants]
    data["current_tenant_id"] = user_obj.current_tenant_id

    return Success(data=data)


async def get_all_parent_menus(menu_ids: set[int]) -> set[int]:
    """递归获取所有父菜单ID
    
    根据给定的菜单ID集合，递归查询所有父级菜单ID，直到parent_id为0为止
    """
    if not menu_ids:
        return set()
    
    all_menu_ids = set(menu_ids)
    current_ids = set(menu_ids)
    
    while current_ids:
        # 查询当前这批菜单的父菜单ID
        menus = await Menu.filter(id__in=current_ids).all()
        parent_ids = {menu.parent_id for menu in menus if menu.parent_id != 0}
        
        # 如果没有新的父菜单，退出循环
        new_parent_ids = parent_ids - all_menu_ids
        if not new_parent_ids:
            break
            
        all_menu_ids.update(new_parent_ids)
        current_ids = new_parent_ids
    
    return all_menu_ids


@router.get("/usermenu", summary="查看用户菜单")
async def get_user_menu(token: str = Header(..., description="token验证")):
    user_obj = await AuthControl.is_authed(token)
    user_id = user_obj.id
    menus: list[Menu] = []

    if user_obj.is_superuser:
        menus = await Menu.all()
    else:
        current_tenant_id = user_obj.current_tenant_id
        if not current_tenant_id:
            user_tenants = await user_controller.get_user_tenants(user_id)
            if user_tenants:
                current_tenant_id = user_tenants[0].id
                await user_controller.set_current_tenant(user_id, current_tenant_id)

        # 通过RelationQuery获取用户在当前租户下的菜单ID集合
        menu_ids = await RelationQuery.get_user_menu_ids(user_id, current_tenant_id)
        if menu_ids:
            # 递归获取所有父菜单ID
            all_menu_ids = await get_all_parent_menus(set(menu_ids))
            menus = await Menu.filter(id__in=all_menu_ids).all()

    # 构建菜单树结构
    menu_map = {menu.id: await menu.to_dict() for menu in menus}
    
    # 找到所有根菜单（parent_id == 0）
    root_menus: list[dict] = []
    for menu in menus:
        if menu.parent_id == 0:
            root_menus.append(menu_map[menu.id])
    
    # 递归构建子菜单树
    def build_menu_tree(parent_id: int) -> list[dict]:
        children = []
        for menu in menus:
            if menu.parent_id == parent_id:
                menu_dict = menu_map[menu.id]
                menu_dict["children"] = build_menu_tree(menu.id)
                children.append(menu_dict)
        # 按order排序
        children.sort(key=lambda x: x.get("order", 0))
        return children
    
    # 为每个根菜单构建树
    res = []
    for root_menu in root_menus:
        root_menu["children"] = build_menu_tree(root_menu["id"])
        res.append(root_menu)
    
    # 按order排序根菜单
    res.sort(key=lambda x: x.get("order", 0))
    
    return Success(data=res)


@router.get("/userapi", summary="查看用户API")
async def get_user_api(token: str = Header(..., description="token验证")):
    user_obj = await AuthControl.is_authed(token)
    user_id = user_obj.id

    if user_obj.is_superuser:
        api_objs: list[Api] = await Api.all()
        apis = [api.method.lower() + api.path for api in api_objs]
        return Success(data=apis)

    current_tenant_id = user_obj.current_tenant_id
    if not current_tenant_id:
        user_tenants = await user_controller.get_user_tenants(user_id)
        if user_tenants:
            current_tenant_id = user_tenants[0].id
            await user_controller.set_current_tenant(user_id, current_tenant_id)

    # 通过RelationQuery获取用户在当前租户下的API权限
    api_ids = await RelationQuery.get_user_api_ids(user_id, current_tenant_id)
    if not api_ids:
        return Success(data=[])

    api_objs = await Api.filter(id__in=api_ids).all()
    apis = list(set(api.method.lower() + api.path for api in api_objs))
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


class QuickLoginSchema(BaseModel):
    target_user_id: int


@router.post("/quick_login", summary="快捷登录到其他用户")
async def quick_login(
    schema: QuickLoginSchema,
    token: str = Header(..., description="token验证"),
):
    """快捷登录功能：允许具有权限的用户快速切换到其他用户
    - 需要用户具有 'post/api/v1/base/quick_login' 权限
    - 不能快捷登录到超级管理员
    - 如果目标用户有多个租户，需要选择租户
    """
    current_user = await AuthControl.is_authed(token)

    target_user = await user_controller.get(id=schema.target_user_id)
    if not target_user:
        return Fail(code=404, msg="目标用户不存在")

    if target_user.is_superuser:
        return Fail(code=403, msg="不能快捷登录到超级管理员账户")

    if not current_user.is_superuser:
        current_tenants = await user_controller.get_user_tenants(current_user.id)
        target_tenants = await user_controller.get_user_tenants(target_user.id)
        current_tenant_ids = {t.id for t in current_tenants}
        target_tenant_ids = {t.id for t in target_tenants}

        if not current_tenant_ids.intersection(target_tenant_ids):
            return Fail(code=403, msg="您没有权限快捷登录到该用户")

    await user_controller.update_last_login(target_user.id)

    tenants = await user_controller.get_user_tenants(target_user.id)
    tenant_list = [{"id": t.id, "name": t.name, "domain": t.domain} for t in tenants]

    current_tenant_id = target_user.current_tenant_id
    tenant_domain = None
    if len(tenant_list) == 1 and not current_tenant_id:
        current_tenant_id = tenant_list[0]["id"]
        tenant_domain = tenant_list[0]["domain"]
        await user_controller.set_current_tenant(target_user.id, current_tenant_id)
    elif current_tenant_id:
        for t in tenant_list:
            if t["id"] == current_tenant_id:
                tenant_domain = t["domain"]
                break

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
                tenant_domain=tenant_domain,
            )
        ),
        username=target_user.username,
        tenants=tenant_list,
        need_select_tenant=len(tenant_list) > 1 and not target_user.is_superuser,
        current_tenant_id=current_tenant_id,
    )
    return Success(data=data.model_dump())
