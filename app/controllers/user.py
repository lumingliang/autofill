from datetime import datetime
from typing import List, Optional

from fastapi.exceptions import HTTPException

from app.core.crud import CRUDBase
from app.models.admin import Tenant, User
from app.schemas.login import CredentialsSchema
from app.schemas.users import UserCreate, UserUpdate
from app.utils.password import get_password_hash, verify_password

from .role import role_controller


class UserController(CRUDBase[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(model=User)

    async def get_by_email(self, email: str) -> Optional[User]:
        return await self.model.filter(email=email).first()

    async def get_by_username(self, username: str) -> Optional[User]:
        return await self.model.filter(username=username).first()

    async def create_user(self, obj_in: UserCreate) -> User:
        obj_in.password = get_password_hash(password=obj_in.password)
        obj = await self.create(obj_in)
        
        # 关联租户
        if obj_in.tenant_ids:
            for tenant_id in obj_in.tenant_ids:
                tenant = await Tenant.filter(id=tenant_id).first()
                if tenant:
                    await obj.tenants.add(tenant)
        
        return obj

    async def update_last_login(self, id: int) -> None:
        user = await self.model.get(id=id)
        user.last_login = datetime.now()
        await user.save()

    async def authenticate(self, credentials: CredentialsSchema) -> Optional["User"]:
        user = await self.model.filter(username=credentials.username).first()
        if not user:
            raise HTTPException(status_code=400, detail="无效的用户名")
        verified = verify_password(credentials.password, user.password)
        if not verified:
            raise HTTPException(status_code=400, detail="密码错误!")
        if not user.is_active:
            raise HTTPException(status_code=400, detail="用户已被禁用")
        return user

    async def update_roles(self, user: User, role_ids: List[int]) -> None:
        await user.roles.clear()
        for role_id in role_ids:
            role_obj = await role_controller.get(id=role_id)
            await user.roles.add(role_obj)

    async def update_tenants(self, user: User, tenant_ids: List[int]) -> None:
        """更新用户关联的租户"""
        await user.tenants.clear()
        for tenant_id in tenant_ids:
            tenant = await Tenant.filter(id=tenant_id).first()
            if tenant:
                await user.tenants.add(tenant)

    async def set_current_tenant(self, user_id: int, tenant_id: int) -> None:
        """设置用户当前选中的租户"""
        user = await self.get(id=user_id)
        # 检查用户是否属于该租户
        tenant_ids = [t.id for t in await user.tenants.all()]
        if tenant_id not in tenant_ids:
            raise HTTPException(status_code=403, detail="用户不属于该租户")
        user.current_tenant_id = tenant_id
        await user.save()

    async def get_user_tenants(self, user_id: int) -> List[Tenant]:
        """获取用户所属的所有租户"""
        user = await self.get(id=user_id)
        return await user.tenants.all()

    async def reset_password(self, user_id: int):
        user_obj = await self.get(id=user_id)
        if user_obj.is_superuser:
            raise HTTPException(status_code=403, detail="不允许重置超级管理员密码")
        user_obj.password = get_password_hash(password="123456")
        await user_obj.save()


user_controller = UserController()
