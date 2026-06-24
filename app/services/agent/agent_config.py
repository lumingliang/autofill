"""
AgentConfig - Agent 配置模型
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Agent 配置模型"""

    name: str = Field(..., description="Agent 唯一标识")
    display_name: str = Field(..., description="可读名称")
    description: str = Field(..., description="描述")

    # 系统提示词章节配置（四选一，优先级从高到低）
    system_prompt_sections: Optional[List[str]] = Field(default=None, description="完整章节列表")
    system_prompt_base: Optional[str] = Field(default=None, description="基础模板名")
    system_prompt_append_sections: Optional[List[str]] = Field(default=None, description="在基础模板后追加的章节")
    system_prompt_remove_sections: Optional[List[str]] = Field(default=None, description="从基础模板中排除的章节")

    system_prompt_separator: str = Field(default="\n\n", description="章节分隔符")
    system_prompt_variables: Dict[str, Any] = Field(default_factory=dict, description="模板额外变量")

    tools: List[str] = Field(default_factory=list, description="允许使用的工具名列表")
    mcp_servers: List[str] = Field(default_factory=list, description="启用的 MCP 服务器名列表（可选，默认全部）")
    skills: List[str] = Field(default_factory=list, description="允许使用的 Skill 名列表（可选，默认全部）")
    model: str = Field(default="qwen3.6-plus-2026-04-02", description="模型名")
    api_key: Optional[str] = Field(default=None, description="API Key（可选，默认从环境/配置读取）")
    base_url: Optional[str] = Field(default=None, description="模型网关地址（可选）")
    temperature: float = Field(default=0.7, description="温度")
    max_iterations: int = Field(default=10, description="最大迭代轮数")
    max_history: int = Field(default=20, description="最大历史轮数")
    enable_streaming: bool = Field(default=True, description="是否支持流式")
    message_builder_options: Dict[str, Any] = Field(default_factory=dict, description="消息构建器选项")
