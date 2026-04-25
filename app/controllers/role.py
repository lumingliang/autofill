from typing import List

from app.core.crud import CRUDBase
from app.core.relation import RelationQuery
from app.models.admin import Api, Menu, Role, Tenant
from app.schemas.roles import RoleCreate, RoleUpdate


class RoleController(CRUDBase[Role, RoleCreate, RoleUpdate]):
    def __init__(self):
        super().__init__(model=Role)

    async def is_exist(self, name: str, tenant_id: int = None) -> bool:
        query = self.model.filter(name=name)
        if tenant_id is not None:
            query = query.filter(tenant_id=tenant_id)
        return await query.exists()

    async def get_by_tenant(self, tenant_id: int) -> List[Role]:
        """获取指定租户的角色"""
        return await self.model.filter(tenant_id=tenant_id).all()

    async def get_system_roles(self) -> List[Role]:
        """获取系统级角色（不归属特定租户）"""
        return await self.model.filter(tenant_id=None).all()

    async def update_roles(self, role: Role, menu_ids: List[int], api_infos: List[dict]) -> None:
        """更新角色的菜单和API权限，采用批量操作"""
        # 批量替换菜单关联
        await RelationQuery.replace_role_menus(role.id, menu_ids)

        # 查询API IDs（批量查询）
        api_ids = []
        if api_infos:
            conditions = []
            for item in api_infos:
                conditions.append(
                    {"path": item.get("path"), "method": item.get("method")}
                )
            # 由于tortoise不支持OR条件批量查询多个path/method组合，这里采用分批IN查询优化
            paths = [item.get("path") for item in api_infos if item.get("path")]
            methods = [item.get("method") for item in api_infos if item.get("method")]
            if paths and methods:
                api_objs = await Api.filter(path__in=paths, method__in=methods).all()
                # 精确匹配 path+method 组合
                target_set = {(item.get("path"), item.get("method")) for item in api_infos}
                api_ids = [a.id for a in api_objs if (a.path, a.method) in target_set]

        # 批量替换API关联
        await RelationQuery.replace_role_apis(role.id, api_ids)

    async def create_tenant_admin_role(self, tenant: Tenant) -> Role:
        """为租户创建管理员角色"""
        role = await Role.create(
            name=f"{tenant.name}管理员",
            desc=f"{tenant.name}租户的管理员角色，拥有所有权限",
            tenant_id=tenant.id,
            is_system=True,
        )

        # 批量关联所有菜单和API
        all_menus = await Menu.all().values("id")
        all_apis = await Api.all().values("id")
        await RelationQuery.batch_add_role_menus([(role.id, m["id"]) for m in all_menus])
        await RelationQuery.batch_add_role_apis([(role.id, a["id"]) for a in all_apis])

        return role


role_controller = RoleController()
