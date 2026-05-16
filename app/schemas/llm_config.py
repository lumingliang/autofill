"""
LLM 配置管理 Schema
"""
from typing import Any, Dict, List

from pydantic import BaseModel, Field


# ==================== LLM 配置管理 Schemas ====================

class LLMConfigCreate(BaseModel):
    name: str = Field(..., max_length=128, description="配置名称")
    model_provider: str = Field(..., max_length=64, description="模型提供商")
    litellm_params: Dict[str, Any] = Field(default_factory=dict, description="LiteLLM 参数配置")
    model_info: Dict[str, Any] = Field(default_factory=dict, description="模型元信息")
    is_active: bool = Field(True, description="是否启用")
    is_default: bool = Field(False, description="是否为默认配置")
    description: str = Field("", description="配置描述")


class LLMConfigUpdate(BaseModel):
    id: int
    name: str = Field("", max_length=128, description="配置名称")
    model_provider: str = Field("", max_length=64, description="模型提供商")
    litellm_params: Dict[str, Any] = Field(default_factory=dict, description="LiteLLM 参数配置")
    model_info: Dict[str, Any] = Field(default_factory=dict, description="模型元信息")
    is_active: bool = Field(True, description="是否启用")
    is_default: bool = Field(False, description="是否为默认配置")
    description: str = Field("", description="配置描述")


class LLMConfigOut(BaseModel):
    id: int
    name: str = ""
    model_provider: str = ""
    litellm_params: Dict[str, Any] = {}
    model_info: Dict[str, Any] = {}
    capabilities: Dict[str, Any] = {}
    is_active: bool = True
    is_default: bool = False
    description: str = ""
    created_at: str = ""
    updated_at: str = ""

    class Config:
        from_attributes = True


class LLMConfigListRequest(BaseModel):
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=100, description="每页数量")
    name: str = Field("", description="配置名称模糊查询")
    model_provider: str = Field("", description="模型提供商筛选")
    is_active: bool = Field(True, description="是否启用筛选")
    tenant_id: int = Field(0, description="租户ID筛选")


class LLMConfigTestRequest(BaseModel):
    id: int = Field(..., description="配置ID")


class LLMConfigResetMethodsRequest(BaseModel):
    id: int = Field(..., description="配置ID")
    methods: List[str] = Field(default=[], description="指定重置的方法列表，不传则重置所有")


class LLMProvider(BaseModel):
    value: str = ""
    label: str = ""


# ==================== LLM 代理请求 Schemas ====================

class LLMProxyRequest(BaseModel):
    system_prompt: str = Field("", description="系统提示词")
    query: str = Field(..., description="用户输入/对话内容")
    tools: List[Dict[str, Any]] = Field(..., description="工具/函数定义列表")
    tool_choice: str = Field("auto", description="工具选择策略")
    context: str = Field("", description="额外上下文")
    preferred_methods: List[str] = Field(default=[], description="手动指定方法优先级列表")
    session_id: str = Field("", description="会话ID，用于多轮对话记忆")
    memory_rounds: int = Field(0, description="记忆轮数限制，0表示使用默认配置")


class LLMProxyResponse(BaseModel):
    code: int = 200
    msg: str = "OK"
    data: Dict[str, Any] = {}


class LLMHealthCheckResponse(BaseModel):
    code: int = 200
    msg: str = "OK"
    data: Dict[str, Any] = {}
