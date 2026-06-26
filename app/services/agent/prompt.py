"""
Agent 提示词与消息构建

复用现有 PromptRenderer、MessageBuilder 和 MCP section 生成能力。
"""
import platform
from datetime import datetime
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.services.agent.mcp_prompt import build_mcp_section
from app.services.agent.message_builder import EnvInfo, MessageBuilder
from app.services.agent.models import AgentSpec
from app.services.agent.prompt_renderer import PromptRenderer


async def build_system_prompt(spec: AgentSpec, prompt_renderer: PromptRenderer) -> str:
    """根据 AgentSpec 构建 system prompt"""
    variables = dict(spec.system_prompt_variables)
    variables["agent_name"] = spec.name
    variables["model_name"] = spec.model

    sections = spec.system_prompt_sections or []
    if "mcp" in sections:
        variables["mcp_section_content"] = await build_mcp_section(spec.mcp_servers)

    return prompt_renderer.render(
        sections=sections,
        separator=spec.system_prompt_separator,
        variables=variables,
    )


def build_user_message(
    query: str,
    inputs: Optional[Dict[str, Any]],
    spec: AgentSpec,
) -> HumanMessage:
    """根据 AgentSpec 构建用户消息

    复用 MessageBuilder 的复合消息能力。
    """
    builder = MessageBuilder()

    env_info = EnvInfo(
        primary_working_directory="/Users/lu/code/code/py/autofill",
        working_directories=["/Users/lu/code/code/py/autofill"],
        operating_system=platform.system().lower(),
        today_date=datetime.now().strftime("%Y-%m-%d"),
        knowledge_cutoff="August 2025",
        model_name=spec.model,
    )
    builder.set_env_info(env_info)

    opts = spec.message_builder_options
    if opts.get("enable_skill_reminder", False):
        builder.enable_skill_reminder()
    if opts.get("enable_language_settings", False):
        builder.enable_language_settings()
    if opts.get("enable_tool_reminder", False):
        builder.enable_tool_reminder()

    content_parts = builder.build_user_message(query, inputs=inputs)
    return HumanMessage(content=content_parts)
