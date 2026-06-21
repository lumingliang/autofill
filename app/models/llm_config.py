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
    """LLM 模型配置表（全局配置）"""
    model_id = fields.CharField(max_length=128, default="", description="Model ID", index=True)
    model_provider = fields.CharField(max_length=64, default="", description="模型提供商", index=True)
    api_key = fields.CharField(max_length=255, default="", description="API Key")
    api_base = fields.CharField(max_length=255, default="", description="API Base URL")
    timeout = fields.IntField(default=60, description="超时时间(秒)")
    capabilities = fields.JSONField(default=dict, description="结构化输出方法能力配置")
    gateway_model_id = fields.CharField(max_length=64, default="", description="LiteLLM网关中的模型ID", index=True)
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

    @property
    def model(self) -> str:
        """
        自动生成模型名称
        如果提供商是 openai，则拼接为 openai/{model_id}
        否则直接返回 model_id
        """
        if self.model_provider == "openai":
            return f"openai/{self.model_id}"
        return self.model_id

    async def to_dict(self) -> dict:
        """转换为字典"""
        data = {
            "id": self.id,
            "model_id": self.model_id,
            "model_provider": self.model_provider,
            "model": self.model,
            "api_key": self.api_key,
            "api_base": self.api_base,
            "timeout": self.timeout,
            "capabilities": self.capabilities,
            "gateway_model_id": self.gateway_model_id,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "description": self.description,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else "",
        }

        return data
