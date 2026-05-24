"""
系统提示词模型
用于存储和管理系统提示词
"""
from tortoise import fields

from app.models.base import BaseModel, TimestampMixin


class SystemPrompt(BaseModel, TimestampMixin):
    """系统提示词表"""
    name = fields.CharField(max_length=128, description="提示词名称", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    content = fields.TextField(description="提示词内容")
    description = fields.TextField(default="", description="提示词描述")
    is_default = fields.BooleanField(default=False, description="是否为默认提示词")
    is_active = fields.BooleanField(default=True, description="是否启用")
    category = fields.CharField(max_length=64, default="general", description="分类: general/choice/text/multi_task")

    class Meta:
        table = "system_prompt"
        unique_together = [("name", "tenant_id")]
