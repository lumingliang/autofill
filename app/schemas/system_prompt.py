"""
系统提示词相关Schema
"""
from typing import Optional

from pydantic import BaseModel, Field


class SystemPromptCreate(BaseModel):
    """创建系统提示词请求"""
    name: str = Field(..., max_length=128, description="提示词名称")
    content: str = Field(..., description="提示词内容")
    description: str = Field(default="", description="提示词描述")
    category: str = Field(default="general", description="分类: general/choice/text/multi_task")
    is_default: bool = Field(default=False, description="是否为默认提示词")
    is_active: bool = Field(default=True, description="是否启用")


class SystemPromptUpdate(BaseModel):
    """更新系统提示词请求"""
    name: Optional[str] = Field(default=None, max_length=128, description="提示词名称")
    content: Optional[str] = Field(default=None, description="提示词内容")
    description: Optional[str] = Field(default=None, description="提示词描述")
    category: Optional[str] = Field(default=None, description="分类")
    is_default: Optional[bool] = Field(default=None, description="是否为默认提示词")
    is_active: Optional[bool] = Field(default=None, description="是否启用")


class SystemPromptResponse(BaseModel):
    """系统提示词响应"""
    id: int
    name: str
    tenant_id: int
    content: str
    description: str
    category: str
    is_default: bool
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SystemPromptListRequest(BaseModel):
    """列表查询请求"""
    category: Optional[str] = Field(default=None, description="分类筛选")
    keyword: Optional[str] = Field(default=None, description="关键词搜索")
    is_default: Optional[bool] = Field(default=None, description="是否默认筛选")
    is_active: Optional[bool] = Field(default=None, description="是否启用筛选")
    tenant_id: Optional[int] = Field(default=None, description="租户ID（超管用）")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class SystemPromptListResponse(BaseModel):
    """列表查询响应"""
    total: int
    items: list
    page: int
    page_size: int
