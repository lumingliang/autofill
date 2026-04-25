from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class BaseUser(BaseModel):
    id: int
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    last_login: Optional[datetime]
    roles: Optional[list] = []
    # 多租户字段
    tenants: Optional[list] = []
    current_tenant_id: Optional[int] = None


class UserCreate(BaseModel):
    email: EmailStr = Field(example="admin@qq.com")
    username: str = Field(example="admin")
    password: str = Field(example="123456")
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    role_ids: Optional[List[int]] = []
    dept_id: Optional[int] = Field(0, description="部门ID")
    # 多租户字段：用户所属的租户ID列表
    tenant_ids: Optional[List[int]] = Field([], description="所属租户ID列表")

    def create_dict(self):
        return self.model_dump(exclude_unset=True, exclude={"role_ids", "tenant_ids"})


class UserUpdate(BaseModel):
    id: int
    email: EmailStr
    username: str
    avatar: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    role_ids: Optional[List[int]] = []
    dept_id: Optional[int] = 0
    # 多租户字段：用户所属的租户ID列表
    tenant_ids: Optional[List[int]] = Field([], description="所属租户ID列表")


class UpdatePassword(BaseModel):
    old_password: str = Field(description="旧密码")
    new_password: str = Field(description="新密码")


class UserQuery(BaseModel):
    """用户查询参数"""
    username: Optional[str] = None
    email: Optional[str] = None
    dept_id: Optional[int] = None
    # 多租户字段：按租户筛选（仅root可见）
    tenant_id: Optional[int] = Field(None, description="租户ID筛选")


class UserTenantSelect(BaseModel):
    """用户选择租户"""
    tenant_id: int = Field(description="租户ID")


class UserUpdateTenantRoles(BaseModel):
    """更新用户在指定租户下的角色"""
    user_id: int = Field(description="用户ID")
    tenant_id: int = Field(description="租户ID")
    role_ids: List[int] = Field(default=[], description="角色ID列表")
