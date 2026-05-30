from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class BaseTenant(BaseModel):
    id: int
    name: str = ""
    domain: str = ""
    is_active: bool = True
    description: str = ""
    created_at: str = ""
    updated_at: str = ""


class TenantCreate(BaseModel):
    name: str = Field(example="租户A")
    domain: str = Field(example="tenant-a")
    description: str = Field("", example="租户描述")
    is_active: bool = True


class TenantUpdate(BaseModel):
    id: int
    name: str = ""
    domain: str = ""
    description: str = ""
    is_active: bool = True


class TenantSelect(BaseModel):
    """租户选择（用于下拉）"""
    id: int
    name: str = ""


class UserTenantSelect(BaseModel):
    """用户选择租户"""
    tenant_id: int


class TenantWithAdmin(BaseModel):
    """创建租户时返回的信息，包含默认管理员账号"""
    tenant: BaseTenant
    admin_role_id: int = 0
    message: str = ""


class BatchAddUsersToTenant(BaseModel):
    """批量添加用户到租户"""
    tenant_id: int
    user_ids: List[int]


class BatchRemoveUsersFromTenant(BaseModel):
    """批量从租户移除用户"""
    tenant_id: int
    user_ids: List[int]


class UserSearchResult(BaseModel):
    """用户搜索结果"""
    id: int
    username: str
    email: str = ""
    is_active: bool = True


class TenantUserResult(BaseModel):
    """租户已分配用户结果"""
    id: int
    username: str
    email: str = ""
    is_active: bool = True
    assigned_at: str = ""
