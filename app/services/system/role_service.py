"""
角色 Service 层

处理角色相关的业务逻辑，包括：
- 角色 CRUD 操作
- 角色-菜单关联管理
- 角色-API关联管理
- 角色-用户关联管理

约束：
- 使用 @atomic 装饰器控制事务
- 不重复判断权限（中间件已完成认证）
- 租户信息从 Ctx 获取
- 不直接查询 Model 层，通过 Repository 层访问数据
"""

from typing import List, Tuple

from fastapi import HTTPException
from tortoise.transactions import atomic

from app.repositories import (
    api_repository,
    menu_repository,
    role_api_repository,
    role_menu_repository,
    role_repository,
    tenant_repository,
    user_repository,
    user_role_repository,
)
from app.schemas.roles import RoleCreate, RoleUpdate
from app.services.permission_cache_service import permission_cache_service


class RoleService:
    """
    角色 Service

    职责：
    - 处理角色相关的业务逻辑
    - 管理角色与菜单、API、用户的关联
    - 调用 Repository 层进行数据操作

    约束：
    - 使用 @atomic 装饰器控制事务
    - 不直接操作数据库，通过 Repository 层访问数据
    - 不处理 HTTP 请求/响应
    - 租户信息从 Ctx 获取，禁止手动传递 tenant_id
    """

    # ==================== 查询方法 ====================

    async def get_role_by_id(self, role_id: int):
        """根据ID获取角色（应用租户过滤）"""
        role = await role_repository.get_by_id(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")
        return role

    async def list_roles(
        self,
        page: int = 1,
        page_size: int = 10,
        role_name: str = "",
        order: List[str] = None
    ) -> Tuple[int, List]:
        """
        查询角色列表

        Args:
            page: 页码
            page_size: 每页数量
            role_name: 角色名称模糊查询
            order: 排序字段列表

        Returns:
            Tuple[int, List]: (总数, 角色列表)
        """
        if order is None:
            order = ["-updated_at"]

        # 调用 Repository 层查询，租户ID从 Ctx 自动获取
        total, roles = await role_repository.list_by_name(
            page=page,
            page_size=page_size,
            role_name=role_name,
            order=order
        )

        return total, roles

    async def get_role_permissions(self, role_id: int) -> Tuple[List[dict], List[dict]]:
        """
        获取角色的菜单和API权限

        Args:
            role_id: 角色ID

        Returns:
            Tuple[List[dict], List[dict]]: (菜单字典列表, API字典列表)
        """
        # 验证角色存在（会自动应用租户过滤）
        await self.get_role_by_id(role_id)

        # 通过 Repository 层获取关联的菜单和API ID
        menu_ids = await role_menu_repository.get_menu_ids_by_role_id(role_id)
        api_ids = await role_api_repository.get_api_ids_by_role_id(role_id)

        # 通过 Repository 层获取详情并转换为字典
        menus = await menu_repository.get_by_ids(menu_ids)
        apis = await api_repository.get_by_ids(api_ids)

        # 转换为字典返回，避免返回 Model 对象
        menu_dicts = [await m.to_dict() for m in menus]
        api_dicts = [await a.to_dict() for a in apis]

        return menu_dicts, api_dicts

    async def get_role_user_ids(self, role_id: int) -> List[int]:
        """获取角色已分配的用户ID列表"""
        return await user_role_repository.get_user_ids_by_role_id(role_id)

    async def get_available_users_for_role(
        self,
        role_id: int,
        page: int = 1,
        page_size: int = 10,
        username: str = ""
    ) -> Tuple[int, List[dict]]:
        """
        获取可分配给角色的用户列表
        基于当前租户自动过滤，由 Repository 层处理
        """
        total, user_objs = await user_repository.list_by_username(
            page=page,
            page_size=page_size,
            username=username
        )
        data = [await obj.to_dict(exclude_fields=["password"]) for obj in user_objs]

        return total, data

    # ==================== 创建方法 ====================

    @atomic()
    async def create_role(self, role_in: RoleCreate):
        """
        创建角色

        使用 @atomic() 事务控制
        """
        # 检查角色名称是否已存在
        existing = await role_repository.get_by_name(role_in.name)
        if existing:
            raise HTTPException(status_code=400, detail="该角色名称已存在")

        # 创建角色（tenant_id 由 BaseRepository.create 自动注入）
        role_data = role_in.model_dump()
        role = await role_repository.create(role_data)

        return role

    # ==================== 更新方法 ====================

    @atomic()
    async def update_role(self, role_in: RoleUpdate):
        """
        更新角色

        使用 @atomic() 事务控制
        """
        # 获取角色
        role = await self.get_role_by_id(role_in.id)

        # 更新角色
        update_data = role_in.model_dump(exclude={"id"}, exclude_unset=True)
        updated_role = await role_repository.update(role_in.id, update_data)

        return updated_role

    @atomic()
    async def update_role_permissions(
        self,
        role_id: int,
        menu_ids: List[int],
        api_codes: List[str]
    ) -> None:
        """
        更新角色的菜单和API权限

        使用 @atomic() 事务控制
        """
        role = await self.get_role_by_id(role_id)

        # 从 role 获取 tenant_id
        tenant_id = role.tenant_id

        # 批量替换菜单关联
        await role_menu_repository.replace_role_menus(role_id, menu_ids, tenant_id=tenant_id)

        # 通过 api_code 查询 API IDs
        api_ids = []
        if api_codes:
            api_objs = await api_repository.get_by_codes(api_codes)
            api_ids = [a.id for a in api_objs]

        # 批量替换API关联
        await role_api_repository.replace_role_apis(role_id, api_ids, tenant_id=tenant_id)

        # 清除该角色下所有用户的权限缓存
        await permission_cache_service.clear_role_users_cache(role_id)

    # ==================== 删除方法 ====================

    @atomic()
    async def delete_role(self, role_id: int) -> None:
        """
        删除角色

        使用 @atomic() 事务控制
        """
        # 获取角色
        role = await self.get_role_by_id(role_id)

        # 删除角色
        await role_repository.delete(role_id)

    # ==================== 用户分配方法 ====================

    @atomic()
    async def assign_users_to_role(
        self,
        role_id: int,
        user_ids: List[int]
    ) -> None:
        """
        为角色分配用户，同时将这些用户关联到角色对应的租户

        使用 @atomic() 事务控制
        """
        role = await self.get_role_by_id(role_id)

        # 获取当前已分配的用户
        current_user_ids = set(await user_role_repository.get_user_ids_by_role_id(role_id))
        new_user_ids = set(user_ids)

        # 计算需要添加和删除的用户
        users_to_add = new_user_ids - current_user_ids
        users_to_remove = current_user_ids - new_user_ids

        # 获取角色对应的租户ID
        tenant_id = role.tenant_id

        # 批量添加新的用户-角色关联
        if users_to_add:
            pairs = [(uid, role_id, tenant_id) for uid in users_to_add]
            await user_role_repository.batch_add_user_roles(pairs)

        # 删除用户-角色关联
        if users_to_remove:
            for user_id in users_to_remove:
                await user_role_repository.delete_by_user_and_role(user_id, role_id)


# 全局 Service 实例
role_service = RoleService()
