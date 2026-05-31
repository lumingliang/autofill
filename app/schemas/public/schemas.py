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


# ==================== 反馈总结相关请求 ====================

class SummaryFeedbackRequest(BasePublicRequest):
    """反馈内容总结请求"""
    order_id: str = Field(..., description="工单ID（唯一标识）")
    brand: str = Field(..., description="品牌")
    feedback_content: str = Field(..., description="反馈内容（需要总结的文本）")
    callback: str = Field(default="", description="回调信息")


# ==================== 规则执行相关请求 ====================

class RuleExecutePromptConfig(BaseModel):
    """规则执行提示词配置"""
    type: str = Field(default="choice", description="任务类型: choice/text")
    select_fields: List[str] = Field(default_factory=list, description="选择字段列表")
    name_fields: List[str] = Field(default_factory=list, description="名称字段列表")
    rule_fields: List[str] = Field(default_factory=list, description="规则字段列表")
    filter: Optional[Dict[str, Any]] = Field(default=None, description="过滤条件")
    name_separator: Optional[str] = Field(default=None, description="名称分隔符")
    system_prompt_name: Optional[str] = Field(default=None, description="该规则特定的系统提示词名称")


class RuleExecuteParam(BaseModel):
    """规则执行参数"""
    rule_name: str = Field(..., description="规则名称")
    prompt: RuleExecutePromptConfig = Field(..., description="提示词配置")


class RuleExecuteRequest(BasePublicRequest):
    """规则执行引擎请求"""
    session_id: str = Field(..., description="会话ID")
    query: str = Field(..., description="用户输入文本")
    method: Optional[str] = Field(default=None, description="LLM调用方法: plain/json_parser，不传则自动判断")
    temperature: float = Field(default=0.7, description="温度参数")
    step: int = Field(default=1, description="当前步骤")
    is_last: bool = Field(default=False, description="是否为最后一步")
    params: List[RuleExecuteParam] = Field(..., description="规则执行参数列表")
    system_prompt: Optional[str] = Field(default=None, description="自定义系统提示词（可选）")
    system_prompt_name: Optional[str] = Field(default=None, description="系统提示词名称（可选）")


class RuleExecuteResultRequest(BasePublicRequest):
    """规则执行结果查询请求"""
    session_id: str = Field(..., description="会话ID")


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
    # LLM/AI填单相关
    "AIFillDataRequest",
    "AIFillDataResultRequest",
    "LLMFillRequest",
    # 反馈总结相关
    "SummaryFeedbackRequest",
    # 规则执行相关
    "RuleExecuteRequest",
    "RuleExecuteResultRequest",
    "RuleExecuteParam",
    "RuleExecutePromptConfig",
]
