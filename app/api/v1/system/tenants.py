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
from tortoise.expressions import Q

from app.api.base import BaseAPI
from app.core.ctx import Ctx
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.tenants import BatchAddUsersToTenant, BatchRemoveUsersFromTenant, TenantCreate, TenantUpdate
from app.services.system.tenant_service import tenant_service
from app.services.system.user_service import user_service

router = APIRouter()


class TenantAPI(BaseAPI):
    """租户管理 API 类"""

    async def list_tenant(
        self,
        page: int = Query(1, description="页码"),
        page_size: int = Query(10, description="每页数量"),
        name: str = Query("", description="租户名称"),
        domain: str = Query("", description="租户域名"),
    ):
        """
        查看租户列表

        仅超级管理员可查看租户列表
        """
        # 要求超级管理员权限
        self.require_superuser()

        # 调用 Service 层查询
        total, tenants = await tenant_service.list_tenants(
            page=page,
            page_size=page_size,
            name=name,
            domain=domain
        )

        data = [await obj.to_dict() for obj in tenants]
        return SuccessExtra(data=data, total=total, page=page, page_size=page_size)

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
            tenant, admin_role = await tenant_service.create_tenant(tenant_in)
            return Success(
                data={
                    "tenant": await tenant.to_dict(),
                    "admin_role_id": admin_role.id,
                    "message": f"租户创建成功，已自动创建管理员角色：{admin_role.name}",
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

    async def tenant_select(
        self,
        keyword: str = Query("", description="搜索关键词（名称或域名）"),
    ):
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


# 创建 API 实例
tenant_api = TenantAPI()


# 注册路由
@router.get("/list", summary="查看租户列表")
async def list_tenant(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    name: str = Query("", description="租户名称"),
    domain: str = Query("", description="租户域名"),
):
    return await tenant_api.list_tenant(page, page_size, name, domain)


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


@router.get("/select", summary="租户下拉选择")
async def tenant_select(keyword: str = Query("", description="搜索关键词")):
    return await tenant_api.tenant_select(keyword)


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
    """
    批量添加用户到租户

    - 支持一次添加多个用户
    - 会自动跳过已存在的用户
    - 返回成功和失败的详细信息
    """
    # 要求超级管理员权限
    tenant_api.require_superuser()

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


@router.get("/search_users", summary="搜索用户（用于分配给租户）")
async def search_users_for_tenant(
    keyword: str = Query("", description="搜索关键词（用户名或邮箱）"),
    exclude_tenant_id: int = Query(None, description="排除已在此租户中的用户"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页数量"),
):
    """
    搜索用户（用于分配给租户）

    - 支持按用户名或邮箱模糊搜索
    - 可以排除已在此租户中的用户
    - 返回分页结果
    """
    # 要求超级管理员权限
    tenant_api.require_superuser()

    try:
        total, users = await tenant_service.search_users_for_tenant(
            keyword=keyword,
            exclude_tenant_id=exclude_tenant_id,
            page=page,
            page_size=page_size
        )
        return SuccessExtra(data=users, total=total, page=page, page_size=page_size)
    except Exception as e:
        return Fail(code=400, msg=str(e))


@router.get("/assigned_users", summary="获取租户已分配的用户列表")
async def get_tenant_assigned_users(
    tenant_id: int = Query(..., description="租户ID"),
    keyword: str = Query("", description="搜索关键词（用户名或邮箱）"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页数量"),
):
    """
    获取租户已分配的用户列表

    - 支持按用户名或邮箱模糊搜索
    - 返回分页结果，包含分配时间
    """
    # 要求超级管理员权限
    tenant_api.require_superuser()

    try:
        total, users = await tenant_service.get_tenant_users_with_detail(
            tenant_id=tenant_id,
            keyword=keyword,
            page=page,
            page_size=page_size
        )
        return SuccessExtra(data=users, total=total, page=page, page_size=page_size)
    except Exception as e:
        return Fail(code=400, msg=str(e))


@router.post("/batch_remove_users", summary="批量从租户移除用户")
async def batch_remove_users_from_tenant(data: BatchRemoveUsersFromTenant):
    """
    批量从租户移除用户

    - 支持一次移除多个用户
    - 会自动跳过不在该租户中的用户
    - 返回成功和失败的详细信息
    """
    # 要求超级管理员权限
    tenant_api.require_superuser()

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
