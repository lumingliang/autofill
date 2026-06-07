"""
租户管理 API 层

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

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.base import BaseAPI
from app.core.ctx import Ctx
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.tenants import (
    BatchAddUsersToTenant,
    BatchRemoveUsersFromTenant,
    TenantAssignedUsersQuery,
    TenantCreate,
    TenantListQuery,
    TenantSearchQuery,
    TenantUpdate,
)
from app.services.system.tenant_service import tenant_service
from app.services.system.user_service import user_service

router = APIRouter()


class TenantAPI(BaseAPI):
    """租户管理 API 类"""

    async def list_tenant(
        self,
        query: TenantListQuery = Depends(),
    ):
        """
        查看租户列表

        仅超级管理员可查看租户列表
        """
        # 要求超级管理员权限
        self.require_superuser()

        # 调用 Service 层查询
        total, tenants = await tenant_service.list_tenants(
            page=query.page,
            page_size=query.page_size,
            name=query.name,
            domain=query.domain
        )

        data = [await obj.to_dict() for obj in tenants]
        return SuccessExtra(data=data, total=total, page=query.page, page_size=query.page_size)

    async def get_tenant(
        self,
        tenant_id: int = Query(..., description="租户ID"),
    ):
        """查看租户详情"""
        # 要求超级管理员权限
        self.require_superuser()

        tenant_obj = await tenant_service.get_tenant_by_id(tenant_id)
        tenant_dict = await tenant_obj.to_dict()
        return Success(data=tenant_dict)

    async def create_tenant(
        self,
        tenant_in: TenantCreate,
    ):
        """
        创建租户

        仅超级管理员可创建租户，自动创建该租户的管理员角色
        """
        # 要求超级管理员权限
        self.require_superuser()

        try:
            tenant = await tenant_service.create_tenant(tenant_in)
            return Success(
                data={
                    "tenant": await tenant.to_dict(),
                    "message": "租户创建成功",
                },
                msg="创建成功",
            )
        except HTTPException as e:
            return Fail(code=e.status_code, msg=e.detail)
        except Exception as e:
            return Fail(code=400, msg=str(e))

    async def update_tenant(
        self,
        tenant_in: TenantUpdate,
    ):
        """更新租户"""
        # 要求超级管理员权限
        self.require_superuser()

        try:
            await tenant_service.update_tenant(tenant_in)
            return Success(msg="更新成功")
        except HTTPException as e:
            return Fail(code=e.status_code, msg=e.detail)
        except Exception as e:
            return Fail(code=400, msg=str(e))

    async def delete_tenant(
        self,
        tenant_id: int = Query(..., description="租户ID"),
    ):
        """删除租户"""
        # 要求超级管理员权限
        self.require_superuser()

        try:
            await tenant_service.delete_tenant(tenant_id)
            return Success(msg="删除成功")
        except HTTPException as e:
            return Fail(code=e.status_code, msg=e.detail)
        except Exception as e:
            return Fail(code=400, msg=str(e))

    async def get_tenant_users(
        self,
        tenant_id: int = Query(..., description="租户ID"),
    ):
        """获取租户下的所有用户"""
        # 要求超级管理员权限
        self.require_superuser()

        try:
            users = await tenant_service.get_tenant_users(tenant_id)
            return Success(data=users)
        except HTTPException as e:
            return Fail(code=e.status_code, msg=e.detail)
        except Exception as e:
            return Fail(code=400, msg=str(e))

    async def add_user_to_tenant(
        self,
        tenant_id: int = Query(..., description="租户ID"),
        user_id: int = Query(..., description="用户ID"),
    ):
        """添加用户到租户"""
        # 要求超级管理员权限
        self.require_superuser()

        try:
            await tenant_service.add_user_to_tenant(tenant_id, user_id)
            return Success(msg="添加成功")
        except HTTPException as e:
            return Fail(code=e.status_code, msg=e.detail)
        except Exception as e:
            return Fail(code=400, msg=str(e))

    async def remove_user_from_tenant(
        self,
        tenant_id: int = Query(..., description="租户ID"),
        user_id: int = Query(..., description="用户ID"),
    ):
        """从租户移除用户"""
        # 要求超级管理员权限
        self.require_superuser()

        try:
            await tenant_service.remove_user_from_tenant(tenant_id, user_id)
            return Success(msg="移除成功")
        except HTTPException as e:
            return Fail(code=e.status_code, msg=e.detail)
        except Exception as e:
            return Fail(code=400, msg=str(e))

    async def batch_add_users_to_tenant(
        self,
        data: BatchAddUsersToTenant,
    ):
        """
        批量添加用户到租户

        - 支持一次添加多个用户
        - 会自动跳过已存在的用户
        - 返回成功和失败的详细信息
        """
        # 要求超级管理员权限
        self.require_superuser()

        try:
            result = await tenant_service.batch_add_users_to_tenant(data.tenant_id, data.user_ids)
            return Success(
                data=result,
                msg=f"成功添加 {result['success_count']} 个用户，失败 {result['failed_count']} 个"
            )
        except HTTPException as e:
            return Fail(code=e.status_code, msg=e.detail)
        except Exception as e:
            return Fail(code=400, msg=str(e))

    async def search_users_for_tenant(
        self,
        query: TenantSearchQuery = Depends(),
    ):
        """
        搜索用户（用于分配给租户）

        - 支持按用户名或邮箱模糊搜索
        - 可以排除已在此租户中的用户
        - 返回分页结果
        """
        # 要求超级管理员权限
        self.require_superuser()

        try:
            total, users = await tenant_service.search_users_for_tenant(
                keyword=query.keyword,
                exclude_tenant_id=query.exclude_tenant_id,
                page=query.page,
                page_size=query.page_size
            )
            return SuccessExtra(data=users, total=total, page=query.page, page_size=query.page_size)
        except Exception as e:
            return Fail(code=400, msg=str(e))

    async def get_tenant_assigned_users(
        self,
        query: TenantAssignedUsersQuery = Depends(),
    ):
        """
        获取租户已分配的用户列表

        - 支持按用户名或邮箱模糊搜索
        - 返回分页结果，包含分配时间
        """
        # 要求超级管理员权限
        self.require_superuser()

        try:
            total, users = await tenant_service.get_tenant_users_with_detail(
                tenant_id=query.tenant_id,
                keyword=query.keyword,
                page=query.page,
                page_size=query.page_size
            )
            return SuccessExtra(data=users, total=total, page=query.page, page_size=query.page_size)
        except Exception as e:
            return Fail(code=400, msg=str(e))

    async def batch_remove_users_from_tenant(
        self,
        data: BatchRemoveUsersFromTenant,
    ):
        """
        批量从租户移除用户

        - 支持一次移除多个用户
        - 会自动跳过不在该租户中的用户
        - 返回成功和失败的详细信息
        """
        # 要求超级管理员权限
        self.require_superuser()

        try:
            result = await tenant_service.batch_remove_users_from_tenant(data.tenant_id, data.user_ids)
            return Success(
                data=result,
                msg=f"成功移除 {result['success_count']} 个用户，失败 {result['failed_count']} 个"
            )
        except HTTPException as e:
            return Fail(code=e.status_code, msg=e.detail)
        except Exception as e:
            return Fail(code=400, msg=str(e))


# 创建 API 实例
tenant_api = TenantAPI()


# 注册路由
@router.get("/list", summary="查看租户列表")
async def list_tenant(query: TenantListQuery = Depends()):
    return await tenant_api.list_tenant(query)


@router.get("/get", summary="查看租户")
async def get_tenant(tenant_id: int = Query(..., description="租户ID")):
    return await tenant_api.get_tenant(tenant_id)


@router.post("/create", summary="创建租户")
async def create_tenant(tenant_in: TenantCreate):
    return await tenant_api.create_tenant(tenant_in)


@router.post("/update", summary="更新租户")
async def update_tenant(tenant_in: TenantUpdate):
    return await tenant_api.update_tenant(tenant_in)


@router.delete("/delete", summary="删除租户")
async def delete_tenant(tenant_id: int = Query(..., description="租户ID")):
    return await tenant_api.delete_tenant(tenant_id)


@router.get("/users", summary="获取租户下的用户")
async def get_tenant_users(tenant_id: int = Query(..., description="租户ID")):
    return await tenant_api.get_tenant_users(tenant_id)


@router.post("/add_user", summary="添加用户到租户")
async def add_user_to_tenant(
    tenant_id: int = Query(..., description="租户ID"),
    user_id: int = Query(..., description="用户ID"),
):
    return await tenant_api.add_user_to_tenant(tenant_id, user_id)


@router.post("/remove_user", summary="从租户移除用户")
async def remove_user_from_tenant(
    tenant_id: int = Query(..., description="租户ID"),
    user_id: int = Query(..., description="用户ID"),
):
    return await tenant_api.remove_user_from_tenant(tenant_id, user_id)


@router.post("/batch_add_users", summary="批量添加用户到租户")
async def batch_add_users_to_tenant(data: BatchAddUsersToTenant):
    return await tenant_api.batch_add_users_to_tenant(data)


@router.get("/search_users", summary="搜索用户（用于分配给租户）")
async def search_users_for_tenant(query: TenantSearchQuery = Depends()):
    return await tenant_api.search_users_for_tenant(query)


@router.get("/assigned_users", summary="获取租户已分配的用户列表")
async def get_tenant_assigned_users(query: TenantAssignedUsersQuery = Depends()):
    return await tenant_api.get_tenant_assigned_users(query)


@router.post("/batch_remove_users", summary="批量从租户移除用户")
async def batch_remove_users_from_tenant(data: BatchRemoveUsersFromTenant):
    return await tenant_api.batch_remove_users_from_tenant(data)
