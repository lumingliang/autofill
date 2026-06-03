from typing import List, Set, Tuple

from app.core.ctx import Ctx
from app.models.admin import Api, Menu, Role, RoleApi, RoleMenu, Tenant, UserRole, UserTenant


class RelationQuery:
    """关联查询工具类，所有多对多/一对多关系查询统一走这里，禁止直接调用模型关系属性"""

    # ==================== 用户-角色 ====================

    @staticmethod
    async def get_role_ids_by_user_id(user_id: int) -> List[int]:
        """根据用户 ID 获取角色 ID 列表"""
        rows = await UserRole.filter(user_id=user_id).values("role_id")
        return [r["role_id"] for r in rows]

    @staticmethod
    async def get_user_ids_by_role_id(role_id: int) -> List[int]:
        """根据角色 ID 获取用户 ID 列表"""
        rows = await UserRole.filter(role_id=role_id).values("user_id")
        return [r["user_id"] for r in rows]

    @staticmethod
    async def batch_get_role_ids_by_user_ids(user_ids: List[int]) -> dict[int, List[int]]:
        """批量获取用户 ID -> 角色 ID 列表的映射"""
        rows = await UserRole.filter(user_id__in=user_ids).values("user_id", "role_id")
        result: dict[int, List[int]] = {}
        for r in rows:
            result.setdefault(r["user_id"], []).append(r["role_id"])
        return result

    @staticmethod
    async def replace_user_roles(user_id: int, role_ids: List[int]) -> None:
        """替换用户的角色关联（先删除再批量插入）"""
        tenant_id = Ctx.get_request_tenant_id()
        await UserRole.filter(user_id=user_id, tenant_id=tenant_id).delete()

        if role_ids:
            await UserRole.bulk_create(
                [UserRole(user_id=user_id, role_id=rid, tenant_id=tenant_id) for rid in set(role_ids)]
            )

    @staticmethod
    async def batch_add_user_roles(user_id_role_id_pairs: List[Tuple[int, int, int]]) -> None:
        """批量添加用户-角色关联（自动去重）"""
        if not user_id_role_id_pairs:
            return
        # 只查询相关用户的数据，减少查询范围
        user_ids = list(set(uid for uid, _, _ in user_id_role_id_pairs))
        existing = await UserRole.filter(user_id__in=user_ids).values("user_id", "role_id")
        existing_set = {(r["user_id"], r["role_id"]) for r in existing}
        to_create = []
        for uid, rid, tid in user_id_role_id_pairs:
            if (uid, rid) not in existing_set:
                to_create.append(UserRole(user_id=uid, role_id=rid, tenant_id=tid))
                existing_set.add((uid, rid))
        if to_create:
            await UserRole.bulk_create(to_create)

    # ==================== 角色-菜单 ====================

    @staticmethod
    async def get_menu_ids_by_role_id(role_id: int) -> List[int]:
        """根据角色 ID 获取菜单 ID 列表"""
        rows = await RoleMenu.filter(role_id=role_id).values("menu_id")
        return [r["menu_id"] for r in rows]

    @staticmethod
    async def get_role_ids_by_menu_id(menu_id: int) -> List[int]:
        """根据菜单 ID 获取角色 ID 列表"""
        rows = await RoleMenu.filter(menu_id=menu_id).values("role_id")
        return [r["role_id"] for r in rows]

    @staticmethod
    async def batch_get_menu_ids_by_role_ids(role_ids: List[int]) -> dict[int, List[int]]:
        """批量获取角色 ID -> 菜单 ID 列表的映射"""
        rows = await RoleMenu.filter(role_id__in=role_ids).values("role_id", "menu_id")
        result: dict[int, List[int]] = {}
        for r in rows:
            result.setdefault(r["role_id"], []).append(r["menu_id"])
        return result

    @staticmethod
    async def replace_role_menus(role_id: int, menu_ids: List[int]) -> None:
        """替换角色的菜单关联（先删除再批量插入）"""
        tenant_id = Ctx.get_request_tenant_id()
        await RoleMenu.filter(role_id=role_id, tenant_id=tenant_id).delete()

        if menu_ids:
            await RoleMenu.bulk_create(
                [RoleMenu(role_id=role_id, menu_id=mid, tenant_id=tenant_id) for mid in set(menu_ids)]
            )

    @staticmethod
    async def batch_add_role_menus(role_id_menu_id_pairs: List[Tuple[int, int]]) -> None:
        """批量添加角色-菜单关联（自动去重）"""
        if not role_id_menu_id_pairs:
            return

        tenant_id = Ctx.get_request_tenant_id()
        # 只查询相关角色的数据，减少查询范围
        role_ids = list(set(rid for rid, _ in role_id_menu_id_pairs))
        existing = await RoleMenu.filter(role_id__in=role_ids, tenant_id=tenant_id).values("role_id", "menu_id")
        existing_set = {(r["role_id"], r["menu_id"]) for r in existing}
        to_create = []
        for rid, mid in role_id_menu_id_pairs:
            if (rid, mid) not in existing_set:
                to_create.append(RoleMenu(role_id=rid, menu_id=mid, tenant_id=tenant_id))
                existing_set.add((rid, mid))
        if to_create:
            await RoleMenu.bulk_create(to_create)

    # ==================== 角色-API ====================

    @staticmethod
    async def get_api_ids_by_role_id(role_id: int) -> List[int]:
        """根据角色 ID 获取 API ID 列表"""
        rows = await RoleApi.filter(role_id=role_id).values("api_id")
        return [r["api_id"] for r in rows]

    @staticmethod
    async def get_role_ids_by_api_id(api_id: int) -> List[int]:
        """根据 API ID 获取角色 ID 列表"""
        rows = await RoleApi.filter(api_id=api_id).values("role_id")
        return [r["role_id"] for r in rows]

    @staticmethod
    async def batch_get_api_ids_by_role_ids(role_ids: List[int]) -> dict[int, List[int]]:
        """批量获取角色 ID -> API ID 列表的映射"""
        rows = await RoleApi.filter(role_id__in=role_ids).values("role_id", "api_id")
        result: dict[int, List[int]] = {}
        for r in rows:
            result.setdefault(r["role_id"], []).append(r["api_id"])
        return result

    @staticmethod
    async def replace_role_apis(role_id: int, api_ids: List[int]) -> None:
        """替换角色的 API 关联（先删除再批量插入）"""
        tenant_id = Ctx.get_request_tenant_id()
        await RoleApi.filter(role_id=role_id, tenant_id=tenant_id).delete()

        if api_ids:
            await RoleApi.bulk_create(
                [RoleApi(role_id=role_id, api_id=aid, tenant_id=tenant_id) for aid in set(api_ids)]
            )

    @staticmethod
    async def batch_add_role_apis(role_id_api_id_pairs: List[Tuple[int, int]]) -> None:
        """批量添加角色-API 关联（自动去重）"""
        if not role_id_api_id_pairs:
            return

        tenant_id = Ctx.get_request_tenant_id()
        # 只查询相关角色的数据，减少查询范围
        role_ids = list(set(rid for rid, _ in role_id_api_id_pairs))
        existing = await RoleApi.filter(role_id__in=role_ids, tenant_id=tenant_id).values("role_id", "api_id")
        existing_set = {(r["role_id"], r["api_id"]) for r in existing}
        to_create = []
        for rid, aid in role_id_api_id_pairs:
            if (rid, aid) not in existing_set:
                to_create.append(RoleApi(role_id=rid, api_id=aid, tenant_id=tenant_id))
                existing_set.add((rid, aid))
        if to_create:
            await RoleApi.bulk_create(to_create)

    # ==================== 用户-租户 ====================

    @staticmethod
    async def get_tenant_ids_by_user_id(user_id: int) -> List[int]:
        """根据用户 ID 获取租户 ID 列表"""
        rows = await UserTenant.filter(user_id=user_id).values("tenant_id")
        return [r["tenant_id"] for r in rows]

    @staticmethod
    async def get_user_ids_by_tenant_id(tenant_id: int) -> List[int]:
        """根据租户 ID 获取用户 ID 列表"""
        rows = await UserTenant.filter(tenant_id=tenant_id).values("user_id")
        return [r["user_id"] for r in rows]

    @staticmethod
    async def batch_get_tenant_ids_by_user_ids(user_ids: List[int]) -> dict[int, List[int]]:
        """批量获取用户 ID -> 租户 ID 列表的映射"""
        rows = await UserTenant.filter(user_id__in=user_ids).values("user_id", "tenant_id")
        result: dict[int, List[int]] = {}
        for r in rows:
            result.setdefault(r["user_id"], []).append(r["tenant_id"])
        return result

    @staticmethod
    async def replace_user_tenants(user_id: int, tenant_id: int) -> None:
        """替换用户的租户关联（先删除再插入单个租户）"""
        await UserTenant.filter(user_id=user_id).delete()
        if tenant_id:
            await UserTenant.create(user_id=user_id, tenant_id=tenant_id)
