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

    def create_dict(self):
        return self.model_dump(exclude_unset=True, exclude={"role_ids"})


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


class UserListQuery(BaseModel):
    """用户列表查询参数"""
    page: int = Field(1, description="页码")
    page_size: int = Field(10, description="每页数量")
    username: str = Field("", description="用户名称，用于搜索")
    email: str = Field("", description="邮箱地址")
    dept_id: int = Field(0, description="部门ID")
    dept_recursive: bool = Field(True, description="是否递归查询子部门")


class UserGet(BaseModel):
    """用户详情查询参数"""
    user_id: int = Field(..., description="用户ID")


class UserDelete(BaseModel):
    """用户删除参数"""
    user_id: int = Field(..., description="用户ID")


class ResetPassword(BaseModel):
    """重置密码参数"""
    user_id: int = Field(..., description="用户ID")


class UserTenantSelect(BaseModel):
    """用户选择租户"""
    tenant_id: int = Field(description="租户ID")


class UserTenantRolesQuery(BaseModel):
    """获取用户租户角色查询参数

    租户ID从 Ctx 自动获取，无需传递
    """
    user_id: int = Field(..., description="用户ID")


class UserUpdateTenantRoles(BaseModel):
    """更新用户在当前租户下的角色

    租户ID从 Ctx 自动获取，无需传递
    - 超管可通过请求参数指定租户（request_tenant_id）
    - 普通账号使用 JWT 中的 current_tenant_id
    """
    user_id: int = Field(description="用户ID")
    role_ids: List[int] = Field(default=[], description="角色ID列表")
