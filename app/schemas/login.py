from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CredentialsSchema(BaseModel):
    username: str = Field(..., description="用户名称", example="admin")
    password: str = Field(..., description="密码", example="123456")


class TenantInfo(BaseModel):
    id: int
    name: str
    domain: str


class JWTOut(BaseModel):
    access_token: str
    username: str
    # 多租户字段
    tenants: Optional[List[TenantInfo]] = []
    need_select_tenant: bool = False
    current_tenant_id: Optional[int] = None


class JWTPayload(BaseModel):
    user_id: int
    username: str
    is_superuser: bool
    exp: datetime
    current_tenant_id: Optional[int] = None
    tenant_domain: Optional[str] = None
