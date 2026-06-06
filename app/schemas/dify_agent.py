"""
Dify Agent 相关 Schemas
"""
from typing import Optional

from pydantic import BaseModel, Field


# ==================== Dify Agent 查询参数 ====================

class DifyAgentListQuery(BaseModel):
    """Dify Agent 列表查询参数"""
    page: int = Field(1, description="页码", ge=1)
    page_size: int = Field(10, description="每页数量", ge=1, le=100)
    name: str = Field("", description="Agent 名称")


# ==================== Dify Agent Schemas ====================

class DifyAgentCreate(BaseModel):
    """创建 Dify Agent 参数"""
    name: str = Field(..., description="Agent 名称", min_length=1, max_length=100)
    api_key: str = Field(..., description="Dify API Key", min_length=1, max_length=255)
    agent_url: str = Field(..., description="Dify Agent URL", min_length=1, max_length=500)
    description: str = Field("", description="描述", max_length=500)
    is_active: bool = Field(True, description="是否启用")


class DifyAgentUpdate(BaseModel):
    """更新 Dify Agent 参数"""
    id: int = Field(..., description="Agent ID")
    name: Optional[str] = Field(None, description="Agent 名称", max_length=100)
    api_key: Optional[str] = Field(None, description="Dify API Key", max_length=255)
    agent_url: Optional[str] = Field(None, description="Dify Agent URL", max_length=500)
    description: Optional[str] = Field(None, description="描述", max_length=500)
    is_active: Optional[bool] = Field(None, description="是否启用")


class DifyAgentOut(BaseModel):
    """Dify Agent 输出"""
    id: int
    name: str = ""
    tenant_id: int = 0
    api_key: str = ""
    agent_url: str = ""
    description: str = ""
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""

    class Config:
        from_attributes = True


# ==================== Open Agent 接口 Schemas ====================

class AgentChatRequest(BaseModel):
    """Agent 对话请求"""
    query: str = Field(..., description="用户输入")
    conversation_id: Optional[str] = Field(None, description="对话ID，用于保持上下文")
    user: Optional[str] = Field(None, description="用户标识")
    inputs: Optional[dict] = Field(None, description="输入参数")


class AgentChatResponse(BaseModel):
    """Agent 对话响应"""
    answer: str = Field("", description="Agent 回答")
    conversation_id: str = Field("", description="对话ID")
    message_id: str = Field("", description="消息ID")
