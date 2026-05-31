"""
用户 Service 层

处理用户相关的业务逻辑，包括：
- 用户 CRUD 操作
- 用户-角色关联管理
- 用户-租户关联管理
- 密码管理
- 租户权限验证

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

from app.core.ctx import Ctx
from app.models.admin import Role, Tenant, User
from app.repositories import (
    dept_closure_repository,
    dept_repository,
    role_repository,
    tenant_repository,
    user_repository,
    user_role_repository,
    user_tenant_repository,
)
from app.schemas.users import UserCreate, UserListQuery, UserUpdate
from app.services.permission_cache_service import permission_cache_service
from app.utils.password import get_password_hash, verify_password


class UserService:
    """
    用户 Service

    职责：
    - 处理用户相关的业务逻辑
    - 管理用户与角色、租户的关联
    - 调用 Repository 层进行数据操作

    约束：
    - 使用 @atomic 装饰器控制事务
    - 不直接操作数据库，通过 Repository 层访问数据
    - 不处理 HTTP 请求/响应
    - 租户信息从 Ctx 获取，禁止手动传递 tenant_id
    """

    # ==================== 查询方法 ====================

    async def get_user_by_id(self, user_id: int) -> User:
        """根据ID获取用户（应用租户过滤）"""
        user = await user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return await user_repository.get_by_email(email)

    async def list_users(
        self,
        query: UserListQuery
    ) -> Tuple[int, List[dict]]:
        """
        查询用户列表并组装完整数据

        Args:
            query: 用户列表查询参数（UserListQuery Schema）

        Returns:
            Tuple[int, List[dict]]: (总数, 用户数据列表)
        """
        # 构建查询条件
        q = Q()
        if query.username:
            q &= Q(username__contains=query.username)
        if query.email:
            q &= Q(email__contains=query.email)
        if query.dept_id > 0:
            if query.dept_recursive:
                descendant_ids = await dept_closure_repository.get_descendant_ids(query.dept_id)
                if descendant_ids:
                    q &= Q(dept_id__in=descendant_ids)
                else:
                    q &= Q(dept_id=query.dept_id)
            else:
                q &= Q(dept_id=query.dept_id)

        # 调用 Repository 层查询，租户ID从 Ctx 自动获取
        total, users = await user_repository.list_by_tenant(
            page=query.page,
            page_size=query.page_size,
            search=q
        )

        # 转换为字典（排除密码）
        data = [await user.to_dict(exclude_fields=["password"]) for user in users]

        # 批量获取用户ID列表
        user_ids = [item["id"] for item in data]

        # 批量获取角色信息
        await self._attach_roles_to_users(data, user_ids)

        # 获取部门信息
        await self._attach_depts_to_users(data)

        return total, data

    async def _attach_roles_to_users(self, data: List[dict], user_ids: List[int]) -> None:
        """为用户数据附加角色信息"""
        user_role_map = await user_role_repository.batch_get_role_ids_by_user_ids(user_ids)
        all_role_ids = set()
        for rids in user_role_map.values():
            all_role_ids.update(rids)

        role_map = {}
        if all_role_ids:
            roles = await role_repository.get_by_ids(list(all_role_ids))
            role_map = {r.id: {"id": r.id, "name": r.name, "tenant_id": r.tenant_id} for r in roles}

        for item in data:
            item["roles"] = [role_map.get(rid) for rid in user_role_map.get(item["id"], []) if role_map.get(rid)]

    async def _attach_depts_to_users(self, data: List[dict]) -> None:
        """为用户数据附加部门信息"""
        for item in data:
            item_dept_id = item.pop("dept_id", 0)
            if item_dept_id > 0:
                dept = await dept_repository.get_by_id(item_dept_id)
                item["dept"] = await dept.to_dict() if dept else {}
            else:
                item["dept"] = {}

    async def get_user_detail(self, user_id: int) -> dict:
        """获取用户详情"""
        user = await self.get_user_by_id(user_id)
        user_dict = await user.to_dict(exclude_fields=["password"])

        # 获取用户角色
        role_ids = await user_role_repository.get_role_ids_by_user_id(user_id)
        if role_ids:
            roles = await role_repository.get_by_ids(role_ids)
            user_dict["roles"] = [{"id": r.id, "name": r.name, "tenant_id": r.tenant_id} for r in roles]
        else:
            user_dict["roles"] = []

        return user_dict

    # ==================== 创建方法 ====================

    @atomic()
    async def create_user(self, user_in: UserCreate) -> User:
        """
        创建用户

        自动处理租户关联和角色关联
        使用 @atomic() 事务控制

        注意：租户ID校验在 API 层通过 BaseAPI.require_tenant_id() 完成
        """
        # 检查邮箱是否已存在
        existing_user = await user_repository.get_by_email(user_in.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="该邮箱已被注册")

        # 加密密码
        create_data = user_in.create_dict()
        create_data["password"] = get_password_hash(user_in.password)

        # 创建用户
        user = await user_repository.create(create_data)

        # 关联角色（租户ID从 Ctx 自动获取）
        if user_in.role_ids:
            await user_role_repository.replace_user_roles(user.id, user_in.role_ids)

        # 关联租户（tenant_id 由 BaseRepository.create 自动注入）
        await user_tenant_repository.create({"user_id": user.id})

        return user

    # ==================== 更新方法 ====================

    @atomic()
    async def update_user(self, user_in: UserUpdate) -> User:
        """
        更新用户

        使用 @atomic() 事务控制
        """
        # 获取用户
        user = await self.get_user_by_id(user_in.id)

        # 更新用户
        update_data = user_in.model_dump(exclude={"id"}, exclude_unset=True)
        updated_user = await user_repository.update(user_in.id, update_data)

        return updated_user

    # ==================== 删除方法 ====================

    @atomic()
    async def delete_user(self, user_id: int) -> None:
        """
        删除用户

        使用 @atomic() 事务控制
        """
        # 获取用户
        user = await self.get_user_by_id(user_id)

        # 禁止删除超管
        if user.is_superuser:
            raise HTTPException(status_code=403, detail="不允许删除超级管理员")

        # 删除用户
        await user_repository.delete(user_id)

    # ==================== 密码管理 ====================

    @atomic()
    async def reset_password(self, user_id: int) -> None:
        """重置密码为默认密码"""
        user = await self.get_user_by_id(user_id)

        if user.is_superuser:
            raise HTTPException(status_code=403, detail="不允许重置超级管理员密码")

        hashed_password = get_password_hash("123456")
        await user_repository.reset_password(user_id, hashed_password)

    @atomic()
    async def update_password(self, user_id: int, old_password: str, new_password: str) -> None:
        """修改密码"""
        user = await self.get_user_by_id(user_id)

        # 验证旧密码
        if not verify_password(old_password, user.password):
            raise HTTPException(status_code=400, detail="旧密码错误")

        hashed_password = get_password_hash(new_password)
        await user_repository.reset_password(user_id, hashed_password)

    # ==================== 租户相关 ====================

    async def get_user_tenants(self, user_id: int) -> List[Tenant]:
        """获取用户所属的所有租户"""
        tenant_ids = await user_tenant_repository.get_tenant_ids_by_user_id(user_id)
        if not tenant_ids:
            return []
        return await tenant_repository.get_by_ids(tenant_ids)

    @atomic()
    async def set_current_tenant(self, user_id: int, tenant_id: int) -> None:
        """设置用户当前选中的租户"""
        user = await self.get_user_by_id(user_id)

        # 超管可以切换到任何租户
        if not user.is_superuser:
            # 普通用户需要检查是否属于该租户
            tenant_ids = await user_tenant_repository.get_tenant_ids_by_user_id(user_id)
            if tenant_id not in tenant_ids:
                raise HTTPException(status_code=403, detail="用户不属于该租户")

        await user_repository.set_current_tenant(user_id, tenant_id)

    async def get_tenant_roles(self) -> List[Role]:
        """获取当前租户下的所有角色（自动应用租户过滤）"""
        return await role_repository.get_all_by_tenant()

    async def get_user_tenant_roles(self, user_id: int) -> List[int]:
        """获取用户在当前租户下的角色ID列表（自动应用租户过滤）"""
        # 获取用户的所有角色
        user_role_ids = await user_role_repository.get_role_ids_by_user_id(user_id)
        if not user_role_ids:
            return []

        # 筛选出属于当前租户的角色（自动应用租户过滤）
        roles = await role_repository.filter_by_kwargs(id__in=user_role_ids)
        return [r.id for r in roles]

    @atomic()
    async def update_user_tenant_roles(
        self,
        user_id: int,
        role_ids: List[int]
    ) -> None:
        """
        更新用户在当前租户下的角色（自动应用租户过滤）

        使用 @atomic() 事务控制

        注意：租户ID校验在 API 层通过 BaseAPI.require_tenant_id() 完成
        """
        # 验证所有角色是否都属于当前租户（自动应用租户过滤）
        if role_ids:
            unique_role_ids = list(set(role_ids))
            valid_roles = await role_repository.filter_by_kwargs(id__in=unique_role_ids)
            if len(valid_roles) != len(unique_role_ids):
                raise HTTPException(status_code=400, detail="部分角色不存在或不属于该租户")

        # 更新用户角色关联（租户ID从 Ctx 自动获取）
        await user_role_repository.replace_user_roles(user_id, role_ids)

        # 清除该用户在该租户下的权限缓存
        target_tenant_id = Ctx.get_effective_tenant_id()
        await permission_cache_service.clear_user_cache(user_id, target_tenant_id)

    # ==================== 认证相关 ====================

    async def authenticate(self, username: str, password: str) -> User:
        """用户认证"""
        # 使用 first 方法不检查租户，因为登录时还没有选择租户
        user = await user_repository.first(username=username)
        if not user:
            raise HTTPException(status_code=400, detail="无效的用户名")

        if not verify_password(password, user.password):
            raise HTTPException(status_code=400, detail="密码错误")

        if not user.is_active:
            raise HTTPException(status_code=400, detail="用户已被禁用")

        return user

    async def update_last_login(self, user_id: int) -> None:
        """更新用户最后登录时间"""
        await user_repository.update_last_login(user_id)

    async def select_tenant(self, user_id: int, tenant_id: int) -> dict:
        """
        选择租户并返回租户信息

        Returns:
            dict: 包含 tenant_domain 的字典
        """
        await self.set_current_tenant(user_id, tenant_id)

        tenant = await tenant_repository.get_by_id(tenant_id)
        return {"tenant_domain": tenant.domain if tenant else ""}

    async def quick_login_validate(
        self,
        current_user_id: int,
        target_user_id: int,
        is_current_superuser: bool
    ) -> User:
        """
        验证快捷登录权限

        Args:
            current_user_id: 当前用户ID
            target_user_id: 目标用户ID
            is_current_superuser: 当前用户是否为超级管理员

        Returns:
            User: 目标用户对象

        Raises:
            HTTPException: 权限验证失败
        """
        target_user = await self.get_user_by_id(target_user_id)

        if target_user.is_superuser:
            raise HTTPException(status_code=403, detail="不能快捷登录到超级管理员账户")

        if not is_current_superuser:
            current_tenants = await self.get_user_tenants(current_user_id)
            target_tenants = await self.get_user_tenants(target_user_id)
            current_tenant_ids = {t.id for t in current_tenants}
            target_tenant_ids = {t.id for t in target_tenants}

            if not current_tenant_ids.intersection(target_tenant_ids):
                raise HTTPException(status_code=403, detail="您没有权限快捷登录到该用户")

        return target_user

    @atomic()
    async def update_avatar(self, user_id: int, avatar_url: str) -> None:
        """
        更新用户头像

        Args:
            user_id: 用户ID
            avatar_url: 头像URL
        """
        await self.get_user_by_id(user_id)
        await user_repository.update(user_id, {"avatar": avatar_url})


# 全局 Service 实例
user_service = UserService()
