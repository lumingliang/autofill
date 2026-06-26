"""
Agent 核心数据模型

包含 Agent 配置、循环检测、终止策略、动作指纹、Trace 事件等模型。
"""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class LoopDetectionConfig(BaseModel):
    """循环检测配置"""

    enabled: bool = True
    window_size: int = 6
    repetition_threshold: int = 3
    similarity_threshold: float = 0.95
    max_fingerprint_args_len: int = 200


class TerminationPolicy(BaseModel):
    """终止策略配置"""

    check_todos: bool = True
    check_sub_agents: bool = True
    check_finish_reason_stop: bool = True
    require_no_tool_calls: bool = True


class AgentSpec(BaseModel):
    """Agent 规格说明（运行时注册/配置加载）"""

    model_config = ConfigDict(extra="ignore")

    name: str
    display_name: str
    description: str

    # 系统提示词章节配置（兼容现有 section 机制）
    system_prompt_sections: Optional[List[str]] = None
    system_prompt_base: Optional[str] = None
    system_prompt_append_sections: Optional[List[str]] = None
    system_prompt_remove_sections: Optional[List[str]] = None
    system_prompt_separator: str = "\n\n"
    system_prompt_variables: Dict[str, Any] = Field(default_factory=dict)

    # 工具与能力（配置文件中历史字段为 tools，通过 alias 兼容）
    toolset: List[str] = Field(default_factory=list, validation_alias="tools")
    skills: List[str] = Field(default_factory=list)
    mcp_servers: List[str] = Field(default_factory=list)

    # 模型
    model: str = "Qwen/Qwen3-8B"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7

    # 控制
    max_iterations: int = 20
    max_sub_agent_depth: int = 5
    loop_detection: LoopDetectionConfig = Field(default_factory=LoopDetectionConfig)
    termination_policy: TerminationPolicy = Field(default_factory=TerminationPolicy)

    message_builder_options: Dict[str, Any] = Field(default_factory=dict)


class Fingerprint(BaseModel):
    """动作指纹"""

    agent_id: str
    call_type: Literal["tool", "sub_agent"]
    name: str
    args_hash: str
    args_preview: str
    todo_count: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TraceEvent(BaseModel):
    """Trace 链路事件"""

    trace_id: str
    parent_trace_id: Optional[str] = None
    step_index: int
    agent_id: str
    session_id: str
    node_name: str
    event_type: str
    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    state_delta: Optional[Dict[str, Any]] = None
    latency_ms: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TerminationResult(BaseModel):
    """终止校验结果"""

    can_finish: bool
    reason: Optional[str] = None
    failed_layer: Optional[str] = None
    finish_reason: Optional[str] = None
