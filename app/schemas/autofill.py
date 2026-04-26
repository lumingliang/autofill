from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== 应用管理 Schemas ====================

class AppCreate(BaseModel):
    app_name: str = Field(..., max_length=128, pattern=r"^[a-zA-Z0-9_]+$")
    tenant_id: int
    description: Optional[str] = None
    dify_url: Optional[str] = None
    dify_api_key: Optional[str] = None


class AppUpdate(BaseModel):
    id: int
    app_name: Optional[str] = Field(None, max_length=128, pattern=r"^[a-zA-Z0-9_]+$")
    description: Optional[str] = None
    dify_url: Optional[str] = None
    dify_api_key: Optional[str] = None
    is_active: Optional[bool] = None


class AppOut(BaseModel):
    id: int
    app_name: str
    tenant_id: int
    api_key: str
    dify_url: Optional[str]
    dify_api_key: Optional[str]
    description: Optional[str]
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


# ==================== 总结模板 Schemas ====================

class SummaryTemplateCreate(BaseModel):
    name: str = Field(..., max_length=256)
    app_name: str = Field(..., max_length=128)
    tenant_id: int
    class_name: str = Field(..., max_length=128)
    summary: Optional[str] = Field(None, max_length=2000)
    template_content: Optional[str] = None


class SummaryTemplateUpdate(BaseModel):
    id: int
    name: Optional[str] = Field(None, max_length=256)
    app_name: Optional[str] = Field(None, max_length=128)
    class_name: Optional[str] = Field(None, max_length=128)
    summary: Optional[str] = Field(None, max_length=2000)
    template_content: Optional[str] = None


class SummaryTemplateOut(BaseModel):
    id: int
    name: str
    app_name: str
    tenant_id: int
    class_name: str
    summary: Optional[str]
    template_content: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


# ==================== 下拉选项 Schemas ====================

class DropdownOptionCreate(BaseModel):
    summary: Optional[str] = Field(None, max_length=2000)
    description: Optional[str] = None
    class_name: str = Field(..., max_length=128)
    tenant_id: int
    app_name: str = Field(..., max_length=128)
    parent_id: int = 0
    option_value: str = Field(..., max_length=512)


class DropdownOptionUpdate(BaseModel):
    id: int
    summary: Optional[str] = Field(None, max_length=2000)
    description: Optional[str] = None
    class_name: Optional[str] = Field(None, max_length=128)
    app_name: Optional[str] = Field(None, max_length=128)
    parent_id: Optional[int] = None
    option_value: Optional[str] = Field(None, max_length=512)


class DropdownOptionOut(BaseModel):
    id: int
    summary: Optional[str]
    description: Optional[str]
    class_name: str
    tenant_id: int
    app_name: str
    parent_id: int
    option_value: str
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class DropdownOptionTreeOut(BaseModel):
    id: int
    option_value: str
    summary: Optional[str]
    description: Optional[str]
    children: Optional[List["DropdownOptionTreeOut"]] = None


# ==================== 填单记录 Schemas ====================

class FillDataRecordCreate(BaseModel):
    session_id: str = Field(..., max_length=256)
    phone: Optional[str] = Field(None, max_length=32)
    user_unique_id: Optional[str] = Field(None, max_length=256)
    user_name: Optional[str] = Field(None, max_length=256)
    app_name: str = Field(..., max_length=128)
    tenant_id: int
    data: Optional[Dict[str, Any]] = None


class FillDataRecordUpdate(BaseModel):
    id: int
    data: Optional[Dict[str, Any]] = None
    phone: Optional[str] = Field(None, max_length=32)
    user_unique_id: Optional[str] = Field(None, max_length=256)
    user_name: Optional[str] = Field(None, max_length=256)


class FillDataRecordOut(BaseModel):
    id: int
    session_id: str
    phone: Optional[str]
    user_unique_id: Optional[str]
    user_name: Optional[str]
    app_name: str
    tenant_id: int
    data: Optional[Dict[str, Any]]
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


# ==================== Dify 调用请求 Schemas ====================

class SummaryTemplateListRequest(BaseModel):
    class_name: Optional[str] = None


class SummaryTemplateDetailRequest(BaseModel):
    id: int


class DropdownOptionListRequest(BaseModel):
    class_name: Optional[str] = None
    parent_id: Optional[int] = 0


class DropdownOptionDetailRequest(BaseModel):
    id: int


class RecordFillDataRequest(BaseModel):
    session_id: str
    phone: Optional[str] = None
    user_unique_id: Optional[str] = None
    user_name: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class AIFillDataRequest(BaseModel):
    session_id: str
    data: Dict[str, Any]
    response_mode: str = "sync"  # sync 或 async


class AIFillDataResultRequest(BaseModel):
    """查询AI填单结果请求"""
    session_id: str
