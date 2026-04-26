from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi.exceptions import HTTPException

from app.core.crud import CRUDBase
from app.core.relation import RelationQuery
from app.models.admin import Role, Tenant, User
from app.schemas.login import CredentialsSchema
from app.schemas.users import UserCreate, UserUpdate
from app.utils.password import get_password_hash, verify_password


class UserController(CRUDBase[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(model=User)

    async def get_by_email(self, email: str) -> Optional[User]:
        return await self.model.filter(email=email).first()

    async def create_user(self, obj_in: UserCreate, tenant_id: int = None) -> User:
        obj_in.password = get_password_hash(password=obj_in.password)
        obj = await self.create(obj_in)

        # 显式批量关联角色，使用传入的tenant_id或从角色获取
        if obj_in.role_ids:
            roles = await Role.filter(id__in=obj_in.role_ids).all()
            # 优先使用传入的tenant_id，否则从角色获取
            role_tenant_id = roles[0].tenant_id if roles else None
            final_tenant_id = tenant_id or role_tenant_id
            await RelationQuery.replace_user_roles(obj.id, obj_in.role_ids, final_tenant_id)

        # 显式关联租户
        if tenant_id:
            await RelationQuery.replace_user_tenants(obj.id, tenant_id)

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

    async def set_current_tenant(self, user_id: int, tenant_id: int) -> None:
        """设置用户当前选中的租户"""
        user = await self.get(id=user_id)
        # 检查用户是否属于该租户
        tenant_ids = await RelationQuery.get_tenant_ids_by_user_id(user_id)
        if tenant_id not in tenant_ids:
            raise HTTPException(status_code=403, detail="用户不属于该租户")
        user.current_tenant_id = tenant_id
        await user.save()

    async def get_user_tenants(self, user_id: int) -> List[Tenant]:
        """获取用户所属的所有租户"""
        return await RelationQuery.get_tenants_by_user_id(user_id)

    async def reset_password(self, user_id: int):
        user_obj = await self.get(id=user_id)
        if user_obj.is_superuser:
            raise HTTPException(status_code=403, detail="不允许重置超级管理员密码")
        user_obj.password = get_password_hash(password="123456")
        await user_obj.save()


user_controller = UserController()
