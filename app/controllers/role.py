from typing import List, Optional

from app.core.crud import CRUDBase
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
        await role.menus.clear()
        for menu_id in menu_ids:
            menu_obj = await Menu.filter(id=menu_id).first()
            await role.menus.add(menu_obj)

        await role.apis.clear()
        for item in api_infos:
            api_obj = await Api.filter(path=item.get("path"), method=item.get("method")).first()
            await role.apis.add(api_obj)

    async def create_tenant_admin_role(self, tenant: Tenant) -> Role:
        """为租户创建管理员角色"""
        # 获取所有菜单和API
        all_menus = await Menu.all()
        all_apis = await Api.all()

        role = await Role.create(
            name=f"{tenant.name}管理员",
            desc=f"{tenant.name}租户的管理员角色，拥有所有权限",
            tenant_id=tenant.id,
            is_system=True,
        )

        # 关联所有菜单和API
        for menu in all_menus:
            await role.menus.add(menu)
        for api in all_apis:
            await role.apis.add(api)

        return role


role_controller = RoleController()
