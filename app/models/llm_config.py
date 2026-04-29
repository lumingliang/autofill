"""
LLM 配置模型
支持多租户，超管创建的配置 tenant_id 为空（全局配置）
其他租户可以查看全局配置和自己的配置
"""
from tortoise import fields

from .base import BaseModel, TimestampMixin


class LLMConfig(BaseModel, TimestampMixin):
    """LLM 配置表"""
    # 基础信息
    name = fields.CharField(max_length=64, description="配置名称", index=True)
    tenant_id = fields.BigIntField(null=True, description="租户ID，null表示全局配置", index=True)
    
    # 模型配置
    model_provider = fields.CharField(max_length=32, description="模型提供商", index=True)
    model_name = fields.CharField(max_length=128, description="模型名称")
    
    # API 配置
    api_key = fields.CharField(max_length=255, description="API密钥")
    api_base = fields.CharField(max_length=255, null=True, description="API基础URL")
    
    # 模型参数
    temperature = fields.FloatField(default=0.7, description="温度参数")
    max_tokens = fields.IntField(default=2048, description="最大token数")
    top_p = fields.FloatField(default=1.0, description="Top P采样")
    
    # 功能开关
    is_active = fields.BooleanField(default=True, description="是否启用", index=True)
    is_default = fields.BooleanField(default=False, description="是否为默认配置", index=True)
    
    # 描述信息
    description = fields.CharField(max_length=500, null=True, description="配置描述")
    
    class Meta:
        table = "llm_config"


class LLMProvider:
    """LLM 提供商常量"""
    OPENAI = "openai"
    AZURE = "azure"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    BAIDU = "baidu"
    ALIBABA = "alibaba"
    ZHIPU = "zhipu"
    DEEPSEEK = "deepseek"
    MOONSHOT = "moonshot"
    QIANFAN = "qianfan"
    XUNFEI = "xunfei"
    MINIMAX = "minimax"
    MODELSCOPE = "modelscope"

    @classmethod
    def get_choices(cls):
        return [
            (cls.OPENAI, "OpenAI"),
            (cls.AZURE, "Azure OpenAI"),
            (cls.ANTHROPIC, "Anthropic"),
            (cls.GOOGLE, "Google"),
            (cls.BAIDU, "百度文心"),
            (cls.ALIBABA, "阿里通义"),
            (cls.ZHIPU, "智谱AI"),
            (cls.DEEPSEEK, "DeepSeek"),
            (cls.MOONSHOT, "Moonshot"),
            (cls.QIANFAN, "千帆大模型"),
            (cls.XUNFEI, "讯飞星火"),
            (cls.MINIMAX, "MiniMax"),
            (cls.MODELSCOPE, "魔搭社区"),
        ]
