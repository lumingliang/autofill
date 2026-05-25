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

    async def update_roles(self, role: Role, menu_ids: List[int], api_codes: List[str]) -> None:
        """更新角色的菜单和API权限，采用批量操作，自动填充tenant_id"""
        # 从role获取tenant_id
        tenant_id = role.tenant_id

        # 批量替换菜单关联
        await RelationQuery.replace_role_menus(role.id, menu_ids, tenant_id=tenant_id)

        # 通过api_code查询API IDs
        api_ids = []
        if api_codes:
            api_objs = await Api.filter(api_code__in=api_codes).all()
            api_ids = [a.id for a in api_objs]

        # 批量替换API关联
        await RelationQuery.replace_role_apis(role.id, api_ids, tenant_id=tenant_id)

    async def create_tenant_admin_role(self, tenant: Tenant) -> Role:
        """为租户创建管理员角色"""
        role = await Role.create(
            name=f"{tenant.name}管理员",
            desc=f"{tenant.name}租户的管理员角色，拥有所有权限",
            tenant_id=tenant.id,
            is_system=True,
        )

        # 批量关联所有菜单和API，填充tenant_id
        all_menus = await Menu.all().values("id")
        all_apis = await Api.all().values("id")
        await RelationQuery.batch_add_role_menus(
            [(role.id, m["id"]) for m in all_menus],
            tenant_id=tenant.id
        )
        await RelationQuery.batch_add_role_apis(
            [(role.id, a["id"]) for a in all_apis],
            tenant_id=tenant.id
        )

        return role


role_controller = RoleController()
