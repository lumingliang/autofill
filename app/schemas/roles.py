from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class BaseRole(BaseModel):
    id: int
    name: str
    desc: str = ""
    users: Optional[list] = []
    menus: Optional[list] = []
    apis: Optional[list] = []
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    # 多租户字段
    tenant_id: Optional[int] = None
    tenant_name: Optional[str] = None
    is_system: bool = False


class RoleCreate(BaseModel):
    name: str = Field(example="管理员")
    desc: str = Field("", example="管理员角色")
    # 多租户字段：所属租户（仅root可见）
    tenant_id: Optional[int] = Field(None, description="所属租户ID")


class RoleUpdate(BaseModel):
    id: int = Field(example=1)
    name: str = Field(example="管理员")
    desc: str = Field("", example="管理员角色")
    # 多租户字段
    tenant_id: Optional[int] = Field(None, description="所属租户ID")


class RoleUpdateMenusApis(BaseModel):
    id: int
    menu_ids: list[int] = []
    api_infos: list[dict] = []


class RoleQuery(BaseModel):
    """角色查询参数"""
    name: Optional[str] = None
    # 多租户字段：按租户筛选（仅root可见）
    tenant_id: Optional[int] = Field(None, description="租户ID筛选")


class RoleAssignUsers(BaseModel):
    """角色分配用户"""
    role_id: int = Field(..., description="角色ID")
    user_ids: List[int] = Field(default=[], description="用户ID列表")
