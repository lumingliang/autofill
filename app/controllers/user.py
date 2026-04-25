from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi.exceptions import HTTPException

from app.core.crud import CRUDBase
from app.core.relation import RelationQuery
from app.models.admin import Tenant, User
from app.schemas.login import CredentialsSchema
from app.schemas.users import UserCreate, UserUpdate
from app.utils.password import get_password_hash, verify_password


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

        # 显式批量关联角色
        if obj_in.role_ids:
            await RelationQuery.replace_user_roles(obj.id, obj_in.role_ids)

        # 显式批量关联租户
        if obj_in.tenant_ids:
            await RelationQuery.replace_user_tenants(obj.id, obj_in.tenant_ids)

        return obj

    def _extract_relation_fields(self, obj_in: UserUpdate) -> Dict[str, Any]:
        """显式提取用户关联字段：role_ids 和 tenant_ids"""
        relation_fields = {}
        if hasattr(obj_in, "role_ids") and obj_in.role_ids is not None:
            relation_fields["role_ids"] = obj_in.role_ids
        if hasattr(obj_in, "tenant_ids") and obj_in.tenant_ids is not None:
            relation_fields["tenant_ids"] = obj_in.tenant_ids
        return relation_fields

    async def _update_relations(self, obj: User, relation_fields: Dict[str, Any]) -> None:
        """显式更新用户关联关系：先组装数据，再批量插入/删除"""
        if "role_ids" in relation_fields:
            await RelationQuery.replace_user_roles(obj.id, relation_fields["role_ids"])
        if "tenant_ids" in relation_fields:
            await RelationQuery.replace_user_tenants(obj.id, relation_fields["tenant_ids"])

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
        """替换用户的角色关联，采用批量操作"""
        await RelationQuery.replace_user_roles(user.id, role_ids)

    async def update_tenants(self, user: User, tenant_ids: List[int]) -> None:
        """更新用户关联的租户，采用批量操作"""
        await RelationQuery.replace_user_tenants(user.id, tenant_ids)

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
