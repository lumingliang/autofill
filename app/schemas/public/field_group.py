"""
字段组相关请求模型
"""
from typing import List

from pydantic import Field

from .base import BasePublicRequest


class FieldGroupRequest(BasePublicRequest):
    """查询字段组配置请求"""
    group_names: List[str] = Field(default_factory=list, description="字段组名称列表（可选，不传则查询所有）")
    field_names: List[str] = Field(default_factory=list, description="字段名称列表（可选，不传则返回所有字段）")
