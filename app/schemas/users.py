from datetime import datetime
from typing import List

from pydantic import BaseModel, EmailStr, Field


class BaseUser(BaseModel):
    id: int
    email: str = ""
    username: str = ""
    is_active: bool = True
    is_superuser: bool = False
    created_at: str = ""
    updated_at: str = ""
    last_login: str = ""
    roles: list = []
    # 多租户字段
    tenants: list = []
    current_tenant_id: int = 0


class UserCreate(BaseModel):
    email: EmailStr = Field(example="admin@qq.com")
    username: str = Field(example="admin")
    password: str = Field(example="123456")
    is_active: bool = True
    is_superuser: bool = False
    role_ids: List[int] = []
    dept_id: int = Field(0, description="部门ID")
    # 多租户字段：超管指定租户ID，普通用户从JWT获取
    tenant_id: int = Field(0, description="租户ID（仅超管有效）")

    def create_dict(self):
        return self.model_dump(exclude_unset=True, exclude={"role_ids", "tenant_id"})


class UserUpdate(BaseModel):
    id: int
    email: EmailStr
    username: str
    avatar: str = ""
    is_active: bool = True
    is_superuser: bool = False
    dept_id: int = 0


class UpdatePassword(BaseModel):
    old_password: str = Field(description="旧密码")
    new_password: str = Field(description="新密码")


class UserQuery(BaseModel):
    """用户查询参数"""
    username: str = ""
    email: str = ""
    dept_id: int = 0
    # 多租户字段：按租户筛选（仅root可见）
    tenant_id: int = Field(0, description="租户ID筛选")


class UserTenantSelect(BaseModel):
    """用户选择租户"""
    tenant_id: int = Field(description="租户ID")


class UserUpdateTenantRoles(BaseModel):
    """更新用户在指定租户下的角色
    - 超管账号：使用传参的tenant_id
    - 普通账号：使用JWT中的current_tenant_id，传参的tenant_id会被忽略
    """
    user_id: int = Field(description="用户ID")
    tenant_id: int = Field(default=0, description="租户ID（仅超管有效）")
    role_ids: List[int] = Field(default=[], description="角色ID列表")
