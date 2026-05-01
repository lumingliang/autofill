from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== 填单页面 Schemas ====================

class FillPageCreate(BaseModel):
    page_name: str = Field(..., max_length=64)
    page_code: str = Field(..., max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    app_id: int
    app_name: Optional[str] = Field(None, max_length=64)
    tenant_id: int
    description: Optional[str] = None
    is_active: Optional[bool] = True


class FillPageUpdate(BaseModel):
    id: int
    page_name: Optional[str] = Field(None, max_length=64)
    page_code: Optional[str] = Field(None, max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    app_id: Optional[int] = None
    app_name: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class FillPageOut(BaseModel):
    id: int
    page_name: str
    page_code: str
    app_id: int
    app_name: str
    tenant_id: int
    description: Optional[str]
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


# ==================== 字段组配置 Schemas ====================

class OutputTemplateItem(BaseModel):
    """输出模板项"""
    template: str
    description: str


class FieldGroupConfigCreate(BaseModel):
    group_name: str = Field(..., max_length=64)
    group_code: str = Field(..., max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    page_id: int
    app_name: Optional[str] = Field(None, max_length=64)
    page_name: Optional[str] = Field(None, max_length=64)
    prompt_template_base: Optional[str] = None
    output_templates: Optional[Dict[str, OutputTemplateItem]] = None
    description: Optional[str] = None
    tenant_id: Optional[int] = None
    is_active: Optional[bool] = True


class FieldGroupConfigUpdate(BaseModel):
    id: int
    group_name: Optional[str] = Field(None, max_length=64)
    group_code: Optional[str] = Field(None, max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    page_id: Optional[int] = None
    app_name: Optional[str] = Field(None, max_length=64)
    page_name: Optional[str] = Field(None, max_length=64)
    prompt_template_base: Optional[str] = None
    output_templates: Optional[Dict[str, OutputTemplateItem]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class FieldGroupConfigOut(BaseModel):
    id: int
    group_name: str
    group_code: str
    app_name: str
    page_id: int
    page_name: str
    prompt_template_base: Optional[str]
    output_templates: Optional[Dict]
    description: Optional[str]
    tenant_id: int
    is_active: bool
    version: int
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


# ==================== 字段明细 Schemas ====================

class OptionItem(BaseModel):
    """选项项"""
    value: str
    label: str
    base_annotation: Optional[str] = ""
    corrections: Optional[List[Dict]] = []
    is_deleted: Optional[bool] = False


class FieldOptions(BaseModel):
    """字段选项配置（select类型）"""
    source: str = Field(default="static", description="选项来源：static/api")
    api_identifier: Optional[str] = None
    last_sync_at: Optional[str] = None
    items: List[OptionItem] = []


class FieldSpecCreate(BaseModel):
    field_group_id: int
    field_name: str = Field(..., max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    field_label: str = Field(..., max_length=128)
    field_type: str = Field(default="text")
    fill_instruction: Optional[str] = None
    options: Optional[FieldOptions] = None
    corrections: Optional[List[Dict]] = None
    is_active: Optional[bool] = True


class FieldSpecUpdate(BaseModel):
    id: int
    field_group_id: Optional[int] = None
    field_name: Optional[str] = Field(None, max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    field_label: Optional[str] = Field(None, max_length=128)
    field_type: Optional[str] = None
    fill_instruction: Optional[str] = None
    options: Optional[FieldOptions] = None
    corrections: Optional[List[Dict]] = None
    is_active: Optional[bool] = None


class FieldSpecOut(BaseModel):
    id: int
    field_group_id: int
    field_name: str
    field_label: str
    field_type: str
    fill_instruction: Optional[str]
    options: Optional[FieldOptions]
    corrections: Optional[List[Dict]]
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


# ==================== 公开接口请求 Schemas ====================

class FieldGroupQueryRequest(BaseModel):
    app_name: Optional[str] = None
    page_name: Optional[str] = None
    field_group_name: Optional[str] = None
    code: Optional[str] = None


class FieldSpecListRequest(BaseModel):
    field_group_id: int


class FieldSpecQueryRequest(BaseModel):
    field_group_id: Optional[int] = None
    field_name: Optional[str] = None
    field_type: Optional[str] = None
