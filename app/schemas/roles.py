from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class BaseRole(BaseModel):
    id: int
    name: str = ""
    desc: str = ""
    users: list = []
    menus: list = []
    apis: list = []
    created_at: str = ""
    updated_at: str = ""
    # 多租户字段
    tenant_id: int = 0
    tenant_name: str = ""
    is_system: bool = False


class RoleCreate(BaseModel):
    name: str = Field(example="管理员")
    desc: str = Field("", example="管理员角色")
    # 多租户字段：所属租户（仅root可见）
    tenant_id: int = Field(0, description="所属租户ID")


class RoleUpdate(BaseModel):
    id: int = Field(example=1)
    name: str = Field(example="管理员")
    desc: str = Field("", example="管理员角色")
    # 多租户字段
    tenant_id: int = Field(0, description="所属租户ID")


class RoleUpdateMenusApis(BaseModel):
    id: int
    menu_ids: list[int] = []
    api_codes: list[str] = []


class RoleQuery(BaseModel):
    """角色查询参数"""
    name: str = ""
    # 多租户字段：按租户筛选（仅root可见）
    tenant_id: int = Field(0, description="租户ID筛选")


class RoleAssignUsers(BaseModel):
    """角色分配用户"""
    role_id: int = Field(..., description="角色ID")
    user_ids: List[int] = Field(default=[], description="用户ID列表")


class RoleListQuery(BaseModel):
    """角色列表查询参数"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=10000, description="每页数量")
    role_name: str = Field("", description="角色名称，用于搜索")


class RoleGetQuery(BaseModel):
    """角色详情查询参数"""
    role_id: int = Field(..., description="角色ID")


class RoleDeleteQuery(BaseModel):
    """角色删除查询参数"""
    role_id: int = Field(..., description="角色ID")


class RoleAuthorizedQuery(BaseModel):
    """角色权限查询参数"""
    id: int = Field(..., description="角色ID")


class RoleUsersQuery(BaseModel):
    """角色用户列表查询参数"""
    role_id: int = Field(..., description="角色ID")


class RoleAvailableUsersQuery(BaseModel):
    """角色可分配用户列表查询参数"""
    role_id: int = Field(..., description="角色ID")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=10000, description="每页数量")
    username: str = Field("", description="用户名搜索")
