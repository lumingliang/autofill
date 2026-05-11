"""
字段组相关请求模型
"""
from typing import Dict, List, Optional

from pydantic import Field

from .base import BasePublicRequest


class FieldGroupRequest(BasePublicRequest):
    """查询字段组配置请求"""
    group_names: List[str] = Field(default_factory=list, description="字段组名称列表（可选，不传则查询所有）")
    field_names: List[str] = Field(default_factory=list, description="字段名称列表（可选，不传则返回所有字段）")


class LLMFillRequest(BasePublicRequest):
    """LLM填单请求"""
    page_name: str = Field(..., description="页面名称（必填）")
    group_names: List[str] = Field(default_factory=list, description="字段组名称列表（可选，不传则查询所有）")
    field_names: List[str] = Field(default_factory=list, description="字段名称列表（可选，不传则返回所有字段）")
    group_fields: Optional[Dict[str, List[str]]] = Field(default=None, description="字段组与字段的映射关系，key为字段组名，value为该组要查询的字段列表（空列表表示查询该组所有字段）")
    query: str = Field(..., description="用户输入的查询内容")
    method: Optional[str] = Field(default=None, description="LLM调用方法（可选），可选值：with_structured_output、bind_tools、custom_fc_non_stream，不传则使用系统默认策略")
    system_prompt: Optional[str] = Field(default=None, description="系统提示词（可选），优先级高于字段组的prompt_template_base")


class OptimizeFieldInstructionRequest(BasePublicRequest):
    """优化字段填写指引请求"""
    page_name: str = Field(..., description="页面名称（必填）")
    group_name: Optional[str] = Field(default=None, description="字段组名称（可选，不传则查询页面下所有字段）")
    field_name: Optional[str] = Field(default=None, description="单个字段名称（可选，传了则只优化该字段）")
    batch_size: int = Field(default=10, description="每批处理的字段数量（默认10个）")
    model: Optional[str] = Field(default=None, description="使用的模型名称（可选，默认使用系统配置）")
