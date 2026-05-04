"""
LLM 配置管理模型
"""
from tortoise import fields

from .base import BaseModel, TimestampMixin


class LLMProvider(BaseModel, TimestampMixin):
    """LLM 提供商表"""
    value = fields.CharField(max_length=64, unique=True, description="提供商标识", index=True)
    label = fields.CharField(max_length=128, default="", description="提供商显示名称")
    description = fields.TextField(default="", description="提供商描述")
    icon = fields.CharField(max_length=255, default="", description="图标URL或类名")
    is_active = fields.BooleanField(default=True, description="是否启用", index=True)
    order = fields.IntField(default=0, description="排序", index=True)

    class Meta:
        table = "llm_provider"

    async def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "value": self.value,
            "label": self.label,
            "description": self.description,
            "icon": self.icon,
            "is_active": self.is_active,
            "order": self.order,
        }


class LLMConfig(BaseModel, TimestampMixin):
    """LLM 模型配置表"""
    name = fields.CharField(max_length=128, default="", description="配置名称", index=True)
    model_provider = fields.CharField(max_length=64, default="", description="模型提供商", index=True)
    litellm_params = fields.JSONField(default=dict, description="LiteLLM 参数配置")
    model_info = fields.JSONField(default=dict, description="模型元信息")
    capabilities = fields.JSONField(default=dict, description="结构化输出方法能力配置")
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    app_name = fields.CharField(max_length=64, default="", description="应用名称", index=True)
    is_active = fields.BooleanField(default=True, description="是否启用", index=True)
    is_default = fields.BooleanField(default=False, description="是否为默认配置", index=True)
    description = fields.TextField(default="", description="配置描述")

    class Meta:
        table = "llm_config"

    @classmethod
    def get_default_capabilities(cls) -> dict:
        """获取默认的能力配置"""
        return {
            "structured_output_methods": {
                "with_structured_output": {
                    "supported": True,
                    "failed_count": 0,
                    "last_error": "",
                    "last_attempt": ""
                },
                "bind_tools_stream": {
                    "supported": True,
                    "failed_count": 0,
                    "last_error": "",
                    "last_attempt": ""
                },
                "custom_fc_non_stream": {
                    "supported": True,
                    "failed_count": 0,
                    "last_error": "",
                    "last_attempt": ""
                },
                "custom_fc_stream": {
                    "supported": True,
                    "failed_count": 0,
                    "last_error": "",
                    "last_attempt": ""
                },
                "pydantic_parser": {
                    "supported": True,
                    "failed_count": 0,
                    "last_error": "",
                    "last_attempt": ""
                },
                "json_parser": {
                    "supported": True,
                    "failed_count": 0,
                    "last_error": "",
                    "last_attempt": ""
                }
            }
        }

    async def to_dict(self) -> dict:
        """转换为字典"""
        data = {
            "id": self.id,
            "name": self.name,
            "model_provider": self.model_provider,
            "litellm_params": self.litellm_params,
            "model_info": self.model_info,
            "capabilities": self.capabilities,
            "tenant_id": self.tenant_id,
            "app_name": self.app_name,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "description": self.description,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else "",
        }

        return data
