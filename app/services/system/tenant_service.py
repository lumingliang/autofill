"""
租户 Service 层

处理租户相关的业务逻辑，包括：
- 租户 CRUD 操作
- 租户-用户关联管理
- 自动创建租户管理员角色

约束：
- 使用 @atomic 装饰器控制事务
- 不重复判断权限（中间件已完成认证）
- 租户信息从 Ctx 获取
- 不直接查询 Model 层，通过 Repository 层访问数据
"""

from typing import List, Optional, Tuple

from fastapi import HTTPException
from tortoise.expressions import Q
from tortoise.transactions import atomic

from app.core.relation import RelationQuery
from app.models.admin import Tenant
from app.repositories import (
    api_repository,
    menu_repository,
    role_repository,
    tenant_repository,
    user_repository,
    user_tenant_repository,
)
from app.schemas.tenants import TenantCreate, TenantUpdate


class TenantService:
    """
    租户 Service

    职责：
    - 处理租户相关的业务逻辑
    - 管理租户与用户的关联
    - 调用 Repository 层进行数据操作

    约束：
    - 使用 @atomic 装饰器控制事务
    - 不直接操作数据库，通过 Repository 层访问数据
    - 不处理 HTTP 请求/响应
    """

    # ==================== 查询方法 ====================

    async def get_tenant_by_id(self, tenant_id: int) -> Tenant:
        """根据ID获取租户"""
        tenant = await tenant_repository.get_by_id(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="租户不存在")
        return tenant

    async def get_tenant_by_domain(self, domain: str) -> Optional[Tenant]:
        """根据域名获取租户"""
        return await tenant_repository.get_by_domain(domain)

    async def list_tenants(
        self,
        page: int = 1,
        page_size: int = 10,
        name: str = "",
        domain: str = ""
    ) -> Tuple[int, List[Tenant]]:
        """
        查询租户列表

        Args:
            page: 页码
            page_size: 每页数量
            name: 租户名称模糊查询
            domain: 域名模糊查询

        Returns:
            Tuple[int, List[Tenant]]: (总数, 租户列表)
        """
        # 构建查询条件
        q = Q()
        if name:
            q &= Q(name__contains=name)
        if domain:
            q &= Q(domain__contains=domain)

        # 调用 Repository 层查询
        total, tenants = await tenant_repository.list(
            page=page,
            page_size=page_size,
            search=q,
            order=["-updated_at"]
        )

        return total, tenants

    async def get_all_active_tenants(self) -> List[Tenant]:
        """获取所有启用的租户（用于下拉选择）"""
        return await tenant_repository.filter_by_kwargs(is_active=True)

    async def search_tenants(self, keyword: str = "") -> List[Tenant]:
        """
        搜索租户（用于下拉选择模糊搜索）

        Args:
            keyword: 搜索关键词（匹配名称或域名）

        Returns:
            List[Tenant]: 租户列表
        """
        if not keyword:
            return await self.get_all_active_tenants()

        # 使用 filter 进行链式查询
        q = Q(is_active=True) & (Q(name__contains=keyword) | Q(domain__contains=keyword))
        return await tenant_repository.filter(q).all()

    # ==================== 创建方法 ====================

    @atomic()
    async def create_tenant(self, tenant_in: TenantCreate) -> Tuple[Tenant, object]:
        """
        创建租户并自动创建管理员角色

        使用 @atomic() 事务控制

        Returns:
            Tuple[Tenant, Role]: (租户对象, 管理员角色对象)
        """
        # 检查域名是否已存在
        existing = await self.get_tenant_by_domain(tenant_in.domain)
        if existing:
            raise HTTPException(status_code=400, detail="租户域名已存在")

        # 创建租户
        tenant_data = tenant_in.model_dump()
        tenant = await tenant_repository.create(tenant_data)

        # 自动创建该租户的管理员角色
        all_menus = await menu_repository.get_all_ids()
        all_apis = await api_repository.get_all_ids()

        admin_role = await role_repository.create({
            "name": f"{tenant.name}管理员",
            "desc": f"{tenant.name}租户的管理员角色，拥有所有权限",
            "tenant_id": tenant.id,
            "is_system": True,
        })

        # 批量关联所有菜单和API
        await RelationQuery.batch_add_role_menus(
            [(admin_role.id, m_id) for m_id in all_menus],
            tenant_id=tenant.id
        )
        await RelationQuery.batch_add_role_apis(
            [(admin_role.id, a_id) for a_id in all_apis],
            tenant_id=tenant.id
        )

        return tenant, admin_role

    # ==================== 更新方法 ====================

    @atomic()
    async def update_tenant(self, tenant_in: TenantUpdate) -> Tenant:
        """
        更新租户

        使用 @atomic() 事务控制
        """
        # 获取租户
        tenant = await self.get_tenant_by_id(tenant_in.id)

        # 如果修改了域名，检查是否已存在
        if tenant_in.domain and tenant_in.domain != tenant.domain:
            existing = await self.get_tenant_by_domain(tenant_in.domain)
            if existing:
                raise HTTPException(status_code=400, detail="租户域名已存在")

        # 更新租户
        update_data = tenant_in.model_dump(exclude={"id"}, exclude_unset=True)
        updated_tenant = await tenant_repository.update(tenant_in.id, update_data)

        return updated_tenant

    # ==================== 删除方法 ====================

    @atomic()
    async def delete_tenant(self, tenant_id: int) -> None:
        """
        删除租户

        使用 @atomic() 事务控制
        """
        # 获取租户
        await self.get_tenant_by_id(tenant_id)

        # 删除租户（关联数据由数据库外键约束处理）
        await tenant_repository.delete(tenant_id)

    # ==================== 用户关联管理 ====================

    async def get_tenant_users(self, tenant_id: int) -> List[dict]:
        """
        获取租户下的所有用户

        注意：此方法使用 user_repository 查询数据，不直接查询 Model 层
        """
        user_ids = await RelationQuery.get_user_ids_by_tenant_id(tenant_id)
        if not user_ids:
            return []

        # 通过 user_repository 查询用户（UserRepository 已禁用租户过滤）
        users = await user_repository.get_users_by_ids(user_ids=user_ids, page=1, page_size=len(user_ids))
        return [{
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active
        } for user in users[1]]

    @atomic()
    async def add_user_to_tenant(self, tenant_id: int, user_id: int) -> None:
        """将用户添加到租户"""
        # 验证租户存在
        await self.get_tenant_by_id(tenant_id)

        # 验证用户存在（通过 Repository 查询，不应用租户过滤）
        user = await user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        # 添加用户到租户
        await user_tenant_repository.create({
            "user_id": user_id,
            "tenant_id": tenant_id
        })

        # 如果用户没有当前租户ID，则设置为这个租户
        if not user.current_tenant_id:
            user.current_tenant_id = tenant_id
            await user.save()

    @atomic()
    async def remove_user_from_tenant(self, tenant_id: int, user_id: int) -> None:
        """从租户移除用户"""
        # 验证租户存在
        await self.get_tenant_by_id(tenant_id)

        # 验证用户存在（通过 Repository 查询，不应用租户过滤）
        user = await user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        # 从租户移除用户
        await user_tenant_repository.filter(
            user_id=user_id,
            tenant_id=tenant_id
        ).delete()

    @atomic()
    async def batch_add_users_to_tenant(self, tenant_id: int, user_ids: List[int]) -> dict:
        """
        批量添加用户到租户

        Args:
            tenant_id: 租户ID
            user_ids: 用户ID列表

        Returns:
            dict: 包含成功和失败的数量
        """
        # 验证租户存在
        await self.get_tenant_by_id(tenant_id)

        success_count = 0
        failed_count = 0
        failed_users = []

        # 批量查询用户是否存在（使用 get_users_by_ids，不应用租户过滤）
        _, existing_users = await user_repository.get_users_by_ids(
            user_ids=user_ids,
            page=1,
            page_size=len(user_ids)
        )
        existing_user_ids = {user.id for user in existing_users}
        # 构建用户ID到用户对象的映射，用于后续更新current_tenant_id
        user_id_to_user = {user.id: user for user in existing_users}

        # 批量查询用户是否已在租户中
        user_tenant_list = await user_tenant_repository.get_all_by_tenant_id(tenant_id)
        existing_tenant_user_ids = {ut.user_id for ut in user_tenant_list}

        for user_id in user_ids:
            try:
                # 验证用户存在
                if user_id not in existing_user_ids:
                    failed_count += 1
                    failed_users.append({"user_id": user_id, "reason": "用户不存在"})
                    continue

                # 检查用户是否已在租户中
                if user_id in existing_tenant_user_ids:
                    failed_count += 1
                    failed_users.append({"user_id": user_id, "reason": "用户已在该租户中"})
                    continue

                # 添加用户到租户
                await user_tenant_repository.create({
                    "user_id": user_id,
                    "tenant_id": tenant_id
                })

                # 如果用户没有当前租户ID，则设置为这个租户
                user = user_id_to_user.get(user_id)
                if user and not user.current_tenant_id:
                    user.current_tenant_id = tenant_id
                    await user.save()

                success_count += 1
            except Exception as e:
                failed_count += 1
                failed_users.append({"user_id": user_id, "reason": str(e)})

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_users": failed_users
        }

    async def search_users_for_tenant(self, keyword: str = "", exclude_tenant_id: int = None, page: int = 1, page_size: int = 20) -> Tuple[int, List[dict]]:
        """
        搜索用户（用于分配给租户）

        注意：此方法需要查询所有用户（跨租户），通过 user_repository 查询

        Args:
            keyword: 搜索关键词（用户名或邮箱）
            exclude_tenant_id: 排除已在此租户中的用户
            page: 页码
            page_size: 每页数量

        Returns:
            Tuple[int, List[dict]]: (总数, 用户列表)
        """
        # 如果指定了租户ID，获取该租户下已有的用户ID列表
        exclude_user_ids = None
        if exclude_tenant_id:
            exclude_user_ids = await user_tenant_repository.get_user_ids_by_tenant_id(exclude_tenant_id)

        # 通过 user_repository 搜索用户（UserRepository 已禁用租户过滤）
        total, users = await user_repository.search_users(
            keyword=keyword,
            exclude_user_ids=exclude_user_ids,
            page=page,
            page_size=page_size
        )

        data = [{
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active
        } for user in users]

        return total, data

    async def get_tenant_users_with_detail(self, tenant_id: int, keyword: str = "", page: int = 1, page_size: int = 20) -> Tuple[int, List[dict]]:
        """
        获取租户下的用户列表（带详细信息）

        注意：此方法使用 user_tenant_repository 和 user_repository 查询数据，
        不直接查询 Model 层，符合分层架构约束。

        Args:
            tenant_id: 租户ID
            keyword: 搜索关键词（用户名或邮箱）
            page: 页码
            page_size: 每页数量

        Returns:
            Tuple[int, List[dict]]: (总数, 用户列表)
        """
        # 验证租户存在
        await self.get_tenant_by_id(tenant_id)

        # 通过 user_tenant_repository 获取该租户下的所有用户关联（禁用租户过滤）
        user_tenant_list = await user_tenant_repository.get_all_by_tenant_id(tenant_id)

        if not user_tenant_list:
            return 0, []

        # 构建用户ID到分配时间的映射（使用 to_dict 自动处理 datetime 序列化）
        user_id_to_assigned_at = {
            ut.user_id: (await ut.to_dict()).get("created_at", "")
            for ut in user_tenant_list
        }
        user_ids = list(user_id_to_assigned_at.keys())

        # 通过 user_repository 查询用户详情（UserRepository 已禁用租户过滤）
        total, users = await user_repository.get_users_by_ids(
            user_ids=user_ids,
            keyword=keyword,
            page=page,
            page_size=page_size
        )

        data = []
        for user in users:
            data.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "assigned_at": user_id_to_assigned_at.get(user.id, "")
            })

        return total, data

    @atomic()
    async def batch_remove_users_from_tenant(self, tenant_id: int, user_ids: List[int]) -> dict:
        """
        批量从租户移除用户

        Args:
            tenant_id: 租户ID
            user_ids: 用户ID列表

        Returns:
            dict: 包含成功和失败的数量
        """
        # 验证租户存在
        await self.get_tenant_by_id(tenant_id)

        success_count = 0
        failed_count = 0
        failed_users = []

        # 批量查询用户是否已在租户中
        user_tenant_list = await user_tenant_repository.get_all_by_tenant_id(tenant_id)
        existing_tenant_user_ids = {ut.user_id for ut in user_tenant_list}

        for user_id in user_ids:
            try:
                # 检查用户是否在此租户中
                if user_id not in existing_tenant_user_ids:
                    failed_count += 1
                    failed_users.append({"user_id": user_id, "reason": "用户不在该租户中"})
                    continue

                # 从租户移除用户
                await user_tenant_repository.filter(
                    user_id=user_id,
                    tenant_id=tenant_id
                ).delete()
                success_count += 1
            except Exception as e:
                failed_count += 1
                failed_users.append({"user_id": user_id, "reason": str(e)})

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_users": failed_users
        }

    # ==================== 下拉选择方法 ====================

    async def get_tenant_select_list(self, keyword: str = "") -> List[dict]:
        """
        获取租户下拉列表（用于选择器）

        支持模糊搜索，仅返回启用的租户

        Args:
            keyword: 搜索关键词

        Returns:
            List[dict]: 租户列表 [{id, name, domain}]
        """
        tenants = await self.search_tenants(keyword)
        return [{"id": t.id, "name": t.name, "domain": t.domain} for t in tenants]


# 全局 Service 实例
tenant_service = TenantService()
