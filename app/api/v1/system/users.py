"""
用户管理 API 层

职责：
- 接收 HTTP 请求
- 参数校验
- 调用 Service 层处理业务逻辑
- 返回响应

约束：
- 禁止直接操作数据库
- 禁止直接访问 Repository 层
- 禁止手动传递 tenant_id（从 Ctx 获取）
- 禁止重复鉴权（中间件已完成）
- 使用 Schema 封装参数
"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.base import BaseAPI
from app.core.ctx import Ctx
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.users import *
from app.services.system.user_service import user_service

router = APIRouter()


class UserAPI(BaseAPI):
    """用户管理 API 类"""

    async def list_user(
        self,
        query: UserListQuery = Depends(),
    ):
        """
        查看用户列表

        - 超管可以查看所有用户，或按租户筛选
        - 普通用户只能查看当前租户的用户
        """
        # 调用 Service 层查询，直接将 Schema 传递到 Service 层
        # Service 层负责组装用户数据（包括角色、租户、部门信息）
        total, data = await user_service.list_users(query)

        return SuccessExtra(data=data, total=total, page=query.page, page_size=query.page_size)

    async def get_user(
        self,
        query: UserGet = Depends(),
    ):
        """
        查看用户详情

        - 超管可以看到用户的租户信息
        """
        user_dict = await user_service.get_user_detail(query.user_id)
        return Success(data=user_dict)

    async def create_user(
        self,
        user_in: UserCreate,
    ):
        """
        创建用户

        - 超管必须指定租户ID（通过 request_tenant_id 参数）
        - 普通用户自动使用当前租户（jwt_tenant_id）
        """
        try:
            # API 层校验租户ID（继承自 BaseAPI）
            self.require_tenant_id()
            await user_service.create_user(user_in)
            return Success(msg="创建成功")
        except HTTPException as e:
            return Fail(code=e.status_code, msg=e.detail)
        except Exception as e:
            return Fail(code=400, msg=str(e))

    async def update_user(
        self,
        user_in: UserUpdate,
    ):
        """
        更新用户
        """
        try:
            await user_service.update_user(user_in)
            return Success(msg="更新成功")
        except Exception as e:
            return Fail(code=400, msg=str(e))

    async def delete_user(
        self,
        query: UserDelete = Depends(),
    ):
        """
        删除用户

        - 禁止删除超级管理员
        """
        try:
            await user_service.delete_user(query.user_id)
            return Success(msg="删除成功")
        except Exception as e:
            return Fail(code=400, msg=str(e))

    async def reset_password(
        self,
        data: ResetPassword,
    ):
        """
        重置密码为默认密码 123456

        - 禁止重置超级管理员密码
        """
        try:
            await user_service.reset_password(data.user_id)
            return Success(msg="密码已重置为123456")
        except Exception as e:
            return Fail(code=400, msg=str(e))

    async def get_my_tenants(self):
        """
        获取当前用户所属的所有租户

        注意：认证在中间件中已完成，直接从 Ctx 获取用户信息
        """
        # 从 Ctx 获取当前用户（中间件已设置）
        current_user = Ctx.get_user()
        tenants = await user_service.get_user_tenants(current_user.id)
        data = [{"id": t.id, "name": t.name, "domain": t.domain} for t in tenants]
        return Success(data=data)

    async def select_tenant(
        self,
        tenant_data: UserTenantSelect,
    ):
        """
        用户选择当前操作的租户

        注意：认证在中间件中已完成，直接从 Ctx 获取用户信息
        """
        # 从 Ctx 获取当前用户（中间件已设置）
        current_user = Ctx.get_user()
        try:
            await user_service.set_current_tenant(current_user.id, tenant_data.tenant_id)
            return Success(msg="租户选择成功")
        except Exception as e:
            return Fail(code=400, msg=str(e))

    async def get_tenant_roles(self):
        """
        获取当前租户下的所有角色，用于给用户分配角色

        租户ID从 Ctx 自动获取，无需传递
        """
        try:
            # API 层校验租户ID（继承自 BaseAPI）
            self.require_tenant_id()
            roles = await user_service.get_tenant_roles()
            data = [await role.to_dict() for role in roles]
            return Success(data=data)
        except HTTPException as e:
            return Fail(code=e.status_code, msg=e.detail)
        except Exception as e:
            return Fail(code=400, msg=str(e))

    async def get_user_tenant_assigned_roles(
        self,
        query: UserTenantRolesQuery = Depends(),
    ):
        """
        获取用户在当前租户下已分配的角色ID列表

        租户ID从 Ctx 自动获取，无需传递
        """
        try:
            # API 层校验租户ID（继承自 BaseAPI）
            self.require_tenant_id()
            role_ids = await user_service.get_user_tenant_roles(query.user_id)
            return Success(data=role_ids)
        except HTTPException as e:
            return Fail(code=e.status_code, msg=e.detail)
        except Exception as e:
            return Fail(code=400, msg=str(e))

    async def update_user_tenant_roles(
        self,
        data: UserUpdateTenantRoles,
    ):
        """
        更新用户在当前租户下的角色分配

        租户ID从 Ctx 自动获取，无需传递
        - 超管可通过请求参数指定租户（request_tenant_id）
        - 普通账号使用 JWT 中的 current_tenant_id
        """
        try:
            # API 层校验租户ID（继承自 BaseAPI）
            self.require_tenant_id()
            await user_service.update_user_tenant_roles(
                user_id=data.user_id,
                role_ids=data.role_ids
            )
            return Success(msg="更新成功")
        except HTTPException as e:
            return Fail(code=e.status_code, msg=e.detail)
        except Exception as e:
            return Fail(code=400, msg=str(e))


# 创建 API 实例
user_api = UserAPI()


# 注册路由
@router.get("/list", summary="查看用户列表")
async def list_user(query: UserListQuery = Depends()):
    return await user_api.list_user(query)


@router.get("/get", summary="查看用户")
async def get_user(query: UserGet = Depends()):
    return await user_api.get_user(query)


@router.post("/create", summary="创建用户")
async def create_user(user_in: UserCreate):
    return await user_api.create_user(user_in)


@router.post("/update", summary="更新用户")
async def update_user(user_in: UserUpdate):
    return await user_api.update_user(user_in)


@router.delete("/delete", summary="删除用户")
async def delete_user(query: UserDelete = Depends()):
    return await user_api.delete_user(query)


@router.post("/reset_password", summary="重置密码")
async def reset_password(data: ResetPassword):
    return await user_api.reset_password(data)


@router.get("/my_tenants", summary="获取我的租户列表")
async def get_my_tenants():
    return await user_api.get_my_tenants()


@router.post("/select_tenant", summary="选择当前租户")
async def select_tenant(tenant_data: UserTenantSelect):
    return await user_api.select_tenant(tenant_data)


@router.get("/tenant_roles", summary="获取当前租户的角色")
async def get_tenant_roles():
    return await user_api.get_tenant_roles()


@router.get("/tenant_assigned_roles", summary="获取用户在当前租户下已分配的角色")
async def get_user_tenant_assigned_roles(query: UserTenantRolesQuery = Depends()):
    return await user_api.get_user_tenant_assigned_roles(query)


@router.post("/update_tenant_roles", summary="更新用户在当前租户下的角色")
async def update_user_tenant_roles(data: UserUpdateTenantRoles):
    return await user_api.update_user_tenant_roles(data)
