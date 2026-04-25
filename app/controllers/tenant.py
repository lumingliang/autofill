from typing import List, Optional

from fastapi.exceptions import HTTPException

from app.core.crud import CRUDBase
from app.models.admin import Role, Tenant, User
from app.schemas.tenants import TenantCreate, TenantUpdate

from .role import role_controller
from .user import user_controller


class TenantController(CRUDBase[Tenant, TenantCreate, TenantUpdate]):
    def __init__(self):
        super().__init__(model=Tenant)

    async def get_by_domain(self, domain: str) -> Optional[Tenant]:
        return await self.model.filter(domain=domain).first()

    async def create_tenant(self, obj_in: TenantCreate) -> Tenant:
        """创建租户并自动创建该租户的管理员角色"""
        # 检查域名是否已存在
        existing = await self.get_by_domain(obj_in.domain)
        if existing:
            raise HTTPException(status_code=400, detail="租户域名已存在")

        # 创建租户
        tenant = await self.create(obj_in)

        # 自动创建该租户的管理员角色（拥有所有菜单和API权限）
        from app.models.admin import Api, Menu

        all_menus = await Menu.all()
        all_apis = await Api.all()

        admin_role = await Role.create(
            name=f"{tenant.name}管理员",
            desc=f"{tenant.name}租户的管理员角色，拥有所有权限",
            tenant_id=tenant.id,
            is_system=True,
        )

        # 关联所有菜单和API
        for menu in all_menus:
            await admin_role.menus.add(menu)
        for api in all_apis:
            await admin_role.apis.add(api)

        return tenant, admin_role

    async def get_tenant_users(self, tenant_id: int) -> List[User]:
        """获取租户下的所有用户"""
        tenant = await self.get(id=tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="租户不存在")
        return await tenant.tenant_users.all()

    async def add_user_to_tenant(self, tenant_id: int, user_id: int):
        """将用户添加到租户"""
        tenant = await self.get(id=tenant_id)
        user = await user_controller.get(id=user_id)
        if not tenant or not user:
            raise HTTPException(status_code=404, detail="租户或用户不存在")
        await tenant.tenant_users.add(user)

    async def remove_user_from_tenant(self, tenant_id: int, user_id: int):
        """从租户移除用户"""
        tenant = await self.get(id=tenant_id)
        user = await user_controller.get(id=user_id)
        if not tenant or not user:
            raise HTTPException(status_code=404, detail="租户或用户不存在")
        await tenant.tenant_users.remove(user)

    async def get_tenant_roles(self, tenant_id: int) -> List[Role]:
        """获取租户下的所有角色"""
        return await Role.filter(tenant_id=tenant_id).all()


tenant_controller = TenantController()
