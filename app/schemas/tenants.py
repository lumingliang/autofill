from datetime import datetime
from typing import List, Optional

from fastapi import Query
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


class TenantListQuery(BaseModel):
    """租户列表查询参数"""
    page: int = Query(1, description="页码", ge=1)
    page_size: int = Query(10, description="每页数量", ge=1, le=100)
    name: str = Query("", description="租户名称")
    domain: str = Query("", description="租户域名")


class TenantSearchQuery(BaseModel):
    """搜索用户查询参数（用于分配给租户）"""
    keyword: str = Query("", description="搜索关键词（用户名或邮箱）")
    exclude_tenant_id: Optional[int] = Query(None, description="排除已在此租户中的用户")
    page: int = Query(1, description="页码", ge=1)
    page_size: int = Query(20, description="每页数量", ge=1, le=100)


class TenantAssignedUsersQuery(BaseModel):
    """获取租户已分配用户列表查询参数"""
    tenant_id: int = Query(..., description="租户ID")
    keyword: str = Query("", description="搜索关键词（用户名或邮箱）")
    page: int = Query(1, description="页码", ge=1)
    page_size: int = Query(20, description="每页数量", ge=1, le=100)


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
