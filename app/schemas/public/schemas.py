"""
Public API 完整请求模型定义
所有public接口的请求参数统一在此定义，通过继承减少重复
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== 基础请求类 ====================

class BasePublicRequest(BaseModel):
    """公开接口基础请求类"""
    pass

    class Config:
        extra = "allow"


class AppBaseRequest(BasePublicRequest):
    """需要应用名称的基础请求"""
    app_name: str = Field(..., description="应用名称（必填）")


class TenantAppBaseRequest(BasePublicRequest):
    """需要租户和应用的基础请求"""
    tenant_id: Optional[int] = Field(default=None, description="租户ID（可选，默认从认证信息获取）")
    app_name: Optional[str] = Field(default=None, description="应用名称（可选，默认从认证信息获取）")


# ==================== 字段明细相关请求 ====================

class FieldSpecListRequest(AppBaseRequest):
    """查询字段明细列表请求"""
    group_names: List[str] = Field(default_factory=list, description="字段组名称列表（可选，不传则查询所有）")
    field_names: List[str] = Field(default_factory=list, description="字段名称列表（可选，不传则返回所有字段）")


class FieldSpecCreateRequest(BasePublicRequest):
    """创建字段明细请求"""
    field_name: str = Field(..., description="字段名（英文）")
    field_label: str = Field(..., description="字段显示名称")
    field_type: str = Field(default="text", description="字段类型: text/select_single/select_multi")
    fill_instruction: str = Field(default="", description="字段填写指引")
    options: Dict[str, Any] = Field(default_factory=dict, description="选项配置")


class FieldItem(BaseModel):
    """字段项定义"""
    field_name: str = Field(..., description="字段名")
    field_label: Optional[str] = Field(default=None, description="字段显示名称")
    field_type: str = Field(default="text", description="字段类型")
    fill_instruction: Optional[str] = Field(default=None, description="字段填写指引")
    options: Optional[Dict[str, Any]] = Field(default=None, description="选项配置")


class UpsertFieldGroupRequest(AppBaseRequest):
    """创建或更新字段组请求"""
    group_name: str = Field(..., description="字段组名称")
    group_code: Optional[str] = Field(default=None, description="字段组编码（可选，不传则自动生成）")
    output_templates: Optional[Dict[str, Any]] = Field(default=None, description="输出模板配置")
    prompt_template_base: Optional[str] = Field(default=None, description="基础提示词模板")
    fields: List[FieldItem] = Field(default_factory=list, description="字段列表")


# ==================== 字段组相关请求 ====================

class FieldGroupRequest(AppBaseRequest):
    """查询字段组配置请求"""
    group_names: List[str] = Field(default_factory=list, description="字段组名称列表")
    field_names: List[str] = Field(default_factory=list, description="字段名称列表")


class FieldGroupDetailRequest(BasePublicRequest):
    """查询字段组详情请求"""
    group_id: int = Field(..., description="字段组ID")


# ==================== 填单数据相关请求 ====================

class RecordFillDataRequest(BasePublicRequest):
    """记录填单数据请求"""
    session_id: str = Field(..., description="会话ID")
    data: Dict[str, Any] = Field(default_factory=dict, description="填单数据")
    phone: Optional[str] = Field(default=None, description="用户手机号")
    user_unique_id: Optional[str] = Field(default=None, description="用户唯一标识")
    user_name: Optional[str] = Field(default=None, description="用户名称")


# ==================== 下拉选项相关请求 ====================

class DropdownOptionListRequest(BasePublicRequest):
    """查询下拉选项列表请求"""
    class_name: Optional[str] = Field(default=None, description="分类名称")
    parent_id: int = Field(default=0, description="父选项ID（0表示查询一级选项）")
    tree: bool = Field(default=False, description="是否返回树形结构")


class DropdownOptionDetailRequest(BasePublicRequest):
    """查询下拉选项详情请求"""
    id: int = Field(..., description="选项ID")


class FirstLevelMenusRequest(BasePublicRequest):
    """获取一级菜单请求"""
    class_name: Optional[str] = Field(default=None, description="分类名称")


class SubmenusTreeRequest(BasePublicRequest):
    """获取子菜单树形结构请求"""
    first_level_value: str = Field(..., description="一级菜单选项值")
    class_name: Optional[str] = Field(default=None, description="分类名称")


# ==================== 模板相关请求 ====================

class SummaryTemplateListRequest(BasePublicRequest):
    """查询模板列表请求"""
    class_name: Optional[str] = Field(default=None, description="分类名称")


class SummaryTemplateDetailRequest(BasePublicRequest):
    """查询模板详情请求"""
    id: int = Field(..., description="模板ID")


# ==================== LLM/AI 填单相关请求 ====================

class AIFillDataRequest(BasePublicRequest):
    """获取AI填单数据请求"""
    session_id: str = Field(..., description="会话ID")
    data: Dict[str, Any] = Field(default_factory=dict, description="请求数据")
    response_mode: str = Field(default="sync", description="响应模式: sync=同步, async=异步")


class AIFillDataResultRequest(BasePublicRequest):
    """查询AI填单异步结果请求"""
    session_id: str = Field(..., description="会话ID")


class LLMFillRequest(AppBaseRequest):
    """LLM填单请求"""
    group_names: List[str] = Field(default_factory=list, description="字段组名称列表")
    field_names: List[str] = Field(default_factory=list, description="字段名称列表")
    system_prompt_group: Optional[str] = Field(default=None, description="指定使用哪个字段组的system_prompt")
    query: str = Field(..., description="用户输入的查询内容")
    additional_data: Optional[Dict[str, Any]] = Field(default=None, description="附加数据，包含预填充的字段值")
    use_additional_data: bool = Field(default=False, description="是否使用附加数据，为true时跳过additional_data中已有字段的LLM提取")


# ==================== 导出所有请求类 ====================

__all__ = [
    # 基础请求类
    "BasePublicRequest",
    "AppBaseRequest",
    "TenantAppBaseRequest",
    # 字段明细相关
    "FieldSpecListRequest",
    "FieldSpecCreateRequest",
    "FieldItem",
    "UpsertFieldGroupRequest",
    # 字段组相关
    "FieldGroupRequest",
    "FieldGroupDetailRequest",
    # 填单数据相关
    "RecordFillDataRequest",
    # 下拉选项相关
    "DropdownOptionListRequest",
    "DropdownOptionDetailRequest",
    "FirstLevelMenusRequest",
    "SubmenusTreeRequest",
    # 模板相关
    "SummaryTemplateListRequest",
    "SummaryTemplateDetailRequest",
    # LLM/AI填单相关
    "AIFillDataRequest",
    "AIFillDataResultRequest",
    "LLMFillRequest",
]
