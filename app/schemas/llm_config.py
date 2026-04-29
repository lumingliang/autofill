"""
LLM 配置 Schema
"""
from typing import Optional

from pydantic import BaseModel, Field


class BaseLLMConfig(BaseModel):
    """LLM配置基础Schema"""
    name: str = Field(..., description="配置名称", max_length=64)
    model_provider: str = Field(..., description="模型提供商", max_length=32)
    model_name: str = Field(..., description="模型名称", max_length=128)
    api_key: str = Field(..., description="API密钥", max_length=255)
    api_base: Optional[str] = Field(None, description="API基础URL", max_length=255)
    temperature: float = Field(0.7, description="温度参数", ge=0.0, le=2.0)
    max_tokens: int = Field(2048, description="最大token数", ge=1, le=8192)
    top_p: float = Field(1.0, description="Top P采样", ge=0.0, le=1.0)
    is_active: bool = Field(True, description="是否启用")
    is_default: bool = Field(False, description="是否为默认配置")
    description: Optional[str] = Field(None, description="配置描述", max_length=500)


class LLMConfigCreate(BaseLLMConfig):
    """创建LLM配置"""
    tenant_id: Optional[int] = Field(None, description="租户ID，null表示全局配置")


class LLMConfigUpdate(BaseLLMConfig):
    """更新LLM配置"""
    id: int = Field(..., description="配置ID")
    tenant_id: Optional[int] = Field(None, description="租户ID")


class LLMConfigResponse(BaseLLMConfig):
    """LLM配置响应"""
    id: int
    tenant_id: Optional[int]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class LLMConfigListRequest(BaseModel):
    """LLM配置列表请求"""
    page: int = Field(1, description="页码")
    page_size: int = Field(10, description="每页数量")
    name: Optional[str] = Field(None, description="配置名称")
    model_provider: Optional[str] = Field(None, description="模型提供商")
    is_active: Optional[bool] = Field(None, description="是否启用")


class LLMProxyRequest(BaseModel):
    """LLM代理请求"""
    query: str = Field(..., description="用户输入或上下文")
    function_schema: dict = Field(..., description="函数调用参数schema")
    app_key: str = Field(..., description="应用密钥")


class LLMProxyResponse(BaseModel):
    """LLM代理响应"""
    success: bool = Field(..., description="是否成功")
    data: Optional[dict] = Field(None, description="结构化输出结果")
    error: Optional[str] = Field(None, description="错误信息")
