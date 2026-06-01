"""
Dify Agent 模型

用于管理 Dify Agent 配置信息
"""
from tortoise import fields

from .base import BaseModel, TimestampMixin


class DifyAgent(BaseModel, TimestampMixin):
    """
    Dify Agent 配置表

    存储 Dify Agent 的配置信息，包括 API Key 和 URL
    """
    name = fields.CharField(max_length=100, description="Agent名称", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    api_key = fields.CharField(max_length=255, description="Dify API Key", index=True)
    agent_url = fields.CharField(max_length=500, description="Dify Agent URL")
    description = fields.CharField(max_length=500, default="", description="描述")
    is_active = fields.BooleanField(default=True, description="是否启用", index=True)

    class Meta:
        table = "dify_agent"
