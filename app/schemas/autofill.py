from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== 应用管理查询参数 ====================

class AppListQuery(BaseModel):
    """应用列表查询参数"""
    page: int = Field(1, description="页码", ge=1)
    page_size: int = Field(10, description="每页数量", ge=1, le=100)
    app_name: str = Field("", description="应用名称")


# ==================== 应用管理 Schemas ====================

class AppCreate(BaseModel):
    app_name: str = Field(..., max_length=128, pattern=r"^[a-zA-Z0-9_]+$")
    tenant_id: int = Field(0, description="租户ID")
    description: str = Field("", description="应用描述")


class AppUpdate(BaseModel):
    id: int
    app_name: str = Field("", max_length=128, pattern=r"^[a-zA-Z0-9_]+$")
    description: str = Field("", description="应用描述")
    is_active: bool = Field(True, description="是否启用")


class AppOut(BaseModel):
    id: int
    app_name: str = ""
    tenant_id: int = 0
    api_key: str = ""
    description: str = ""
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""

    class Config:
        from_attributes = True


# ==================== 填单记录 Schemas ====================

class FillDataRecordCreate(BaseModel):
    session_id: str = Field(..., max_length=256)
    phone: str = Field("", max_length=32)
    user_unique_id: str = Field("", max_length=256)
    user_name: str = Field("", max_length=256)
    app_name: str = Field(..., max_length=128)
    tenant_id: int = Field(0, description="租户ID")
    data: Dict[str, Any] = Field(default_factory=dict, description="填单数据")


class FillDataRecordUpdate(BaseModel):
    id: int
    data: Dict[str, Any] = Field(default_factory=dict, description="填单数据")
    phone: str = Field("", max_length=32)
    user_unique_id: str = Field("", max_length=256)
    user_name: str = Field("", max_length=256)


class FillDataRecordOut(BaseModel):
    id: int
    session_id: str = ""
    phone: str = ""
    user_unique_id: str = ""
    user_name: str = ""
    app_name: str = ""
    tenant_id: int = 0
    data: Dict[str, Any] = {}
    # AI填单相关字段
    status: str = ""
    result: Dict[str, Any] = {}
    error_msg: str = ""
    processed_at: str = ""
    created_at: str = ""
    updated_at: str = ""

    class Config:
        from_attributes = True


# ==================== Dify 调用请求 Schemas ====================

class SummaryTemplateListRequest(BaseModel):
    class_name: str = Field("", description="分类名称")


class SummaryTemplateDetailRequest(BaseModel):
    id: int


class DropdownOptionListRequest(BaseModel):
    class_name: str = Field("", description="分类名称")
    parent_id: int = Field(0, description="父选项ID")
    tree: bool = Field(False, description="是否返回树形结构，true时递归返回所有子级")


class DropdownOptionDetailRequest(BaseModel):
    id: int


class RecordFillDataRequest(BaseModel):
    session_id: str
    phone: str = Field("", description="手机号")
    user_unique_id: str = Field("", description="用户唯一标识")
    user_name: str = Field("", description="用户名称")
    data: Dict[str, Any] = Field(default_factory=dict, description="填单数据")


class AIFillDataRequest(BaseModel):
    session_id: str
    data: Dict[str, Any]
    response_mode: str = Field(default="sync", description="响应模式: sync 或 async")


class AIFillDataResultRequest(BaseModel):
    """查询AI填单结果请求"""
    session_id: str
