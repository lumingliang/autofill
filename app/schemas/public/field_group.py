"""
字段组相关请求模型
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import BasePublicRequest


class FieldGroupRequest(BasePublicRequest):
    """查询字段组配置请求"""
    group_names: List[str] = Field(default_factory=list, description="字段组名称列表（可选，不传则查询所有）")
    field_names: List[str] = Field(default_factory=list, description="字段名称列表（可选，不传则返回所有字段）")


# ==================== 响应模型 ====================

class StepLLMFillResponseData(BaseModel):
    """分步LLM填单响应数据"""
    session_id: str = Field(..., description="会话ID")
    step: int = Field(..., description="当前步骤序号")
    is_last: bool = Field(..., description="是否为最后一步")
    status: str = Field(..., description="处理状态：completed 或 processing")
    elapsed_time: float = Field(..., description="处理耗时（秒）")
    result: Optional[Dict[str, Any]] = Field(default=None, description="填单结果")
    output_templates: Optional[Dict[str, str]] = Field(default=None, description="输出模板结果，key为字段组名，value为替换后的模板字符串")
    merged_fields: Optional[Dict[str, Any]] = Field(default=None, description="合并后的字段结果（最后一步时返回）")
    meta: Optional[Dict[str, Any]] = Field(default=None, description="LLM调用元数据")
    debug: Optional[Dict[str, Any]] = Field(default=None, description="调试信息")


class StepLLMFillResponse(BaseModel):
    """分步LLM填单标准响应"""
    code: int = Field(default=200, description="响应码")
    msg: str = Field(default="OK", description="响应消息")
    data: StepLLMFillResponseData = Field(..., description="响应数据")


class LLMFillRequest(BasePublicRequest):
    """LLM填单请求"""
    field_names: List[str] = Field(default_factory=list, description="字段名称列表（可选，不传则返回所有字段）")
    group_names: List[str] = Field(default_factory=list, description="字段组名称列表（可选，不传则查询所有）")
    system_prompt_group: Optional[str] = Field(default=None, description="用于获取system_prompt的字段组名（可选，不传则使用第一个group_name）")
    query: str = Field(..., description="用户输入的查询内容")
    method: Optional[str] = Field(default=None, description="LLM调用方法（可选），可选值：with_structured_output、bind_tools、custom_fc_non_stream，不传则使用系统默认策略")
    system_prompt: Optional[str] = Field(default=None, description="系统提示词（可选），优先级最高")
    include_reason: bool = Field(default=False, description="是否返回字段填写理由（可选，默认false），开启后会为每个字段返回填写理由")
    memory_rounds: int = Field(default=0, description="保留历史消息的轮数（可选，默认0，即不保留历史消息）")


class StepLLMFillRequest(BasePublicRequest):
    """分步LLM填单请求 - 新格式"""
    session_id: str = Field(..., description="会话ID（必填），用于标识同一轮填单流程")
    field_names: List[str] = Field(default_factory=list, description="字段名称列表（可选，不传则返回所有字段）")
    group_names: List[str] = Field(default_factory=list, description="字段组名称列表（可选，不传则查询所有）")
    system_prompt_group: Optional[str] = Field(default=None, description="用于获取system_prompt的字段组名（可选，不传则使用第一个group_name）")
    query: str = Field(..., description="用户输入的查询内容")
    method: Optional[str] = Field(default="pydantic_parser", description="LLM调用方法（可选），默认使用pydantic_parser")
    system_prompt: Optional[str] = Field(default=None, description="系统提示词（可选），优先级最高")
    include_reason: bool = Field(default=False, description="是否返回字段填写理由（可选，默认false）")
    memory_rounds: int = Field(default=0, description="保留历史消息的轮数（可选，默认0）")
    is_last: bool = Field(default=False, description="是否为最后一次调用（可选，默认false），为true时会结束填单流程")
    additional_data: Optional[Dict[str, Any]] = Field(default=None, description="附加数据（可选）")
    use_additional_data: bool = Field(default=False, description="是否使用附加数据（可选，默认false）")


class StepLLMFillResultRequest(BaseModel):
    """获取分步填单结果请求"""
    session_id: str = Field(..., description="会话ID（必填）")

    class Config:
        extra = "allow"  # 允许额外字段


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(..., description="角色：user 或 assistant")
    content: str = Field(..., description="消息内容")
    timestamp: Optional[str] = Field(default=None, description="时间戳")


class ChatSessionRequest(BaseModel):
    """聊天会话请求"""
    session_id: Optional[str] = Field(default=None, description="会话ID（可选，不传则创建新会话）")
    system_prompt: Optional[str] = Field(default=None, description="系统提示词（可选）")
    message: str = Field(..., description="用户消息")
    clear_history: bool = Field(default=False, description="是否清空历史记录（可选，默认false）")


class TestFillRequest(BasePublicRequest):
    """测试填单请求"""
    group_names: List[str] = Field(default_factory=list, description="字段组名称列表")
    field_names: List[str] = Field(default_factory=list, description="字段名称列表")
    chat_record: str = Field(..., description="聊天记录内容（必填）")
