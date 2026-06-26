"""
run_agent 工具 - 供 LLM 调用以调度子 Agent

实际调度逻辑由状态图的 sub_agent_dispatch 节点处理，本工具仅作为 LLM 可见的 schema 与占位执行入口。
"""
from typing import Any, Dict, Optional

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, ConfigDict, Field


class RunAgentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str = Field(
        description='The child agent name to invoke. E.g., "autofill" or "echo"'
    )
    query: str = Field(
        description=(
            "The task/query you want to send to the child agent. "
            "This will be treated as the child agent's initial user message. "
            "Write a clear and self-contained instruction, just like a user manually sending a query to that agent."
        )
    )
    inputs: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional extra inputs/context passed to the child agent"
    )
    inherit_context: bool = Field(
        default=True,
        description="Whether to inherit parent tenant_id/user_id/trace_id"
    )
    max_iterations: Optional[int] = Field(
        default=None,
        description="Max iterations allowed for the child agent"
    )


def _run_agent_description() -> str:
    return """Invoke and run a child agent as a tool call.

<run_agent_instructions>
When you need to delegate a sub-task to another specialized agent, invoke this tool.
The child agent will run independently with its own conversation history and tool view, and its final answer will be returned to you as a tool result.

How to use run_agent:
- Call this tool with the child agent name and a clear `query` (the task you want it to perform).
- The `query` is sent as the child agent's initial user message, exactly like a user manually sending that query to the child agent.
- The child agent will execute autonomously until it terminates, then its final answer will be delivered back as the result of this tool call.
- Do not describe the call in your text response; actually invoke this tool.

Important:
- When a sub-agent is needed, you must invoke this tool IMMEDIATELY instead of describing the plan in text.
- NEVER just announce "I will ask the xxx agent" without calling this tool.
- This is a BLOCKING REQUIREMENT: invoke run_agent BEFORE producing any other response about the delegated task.
- The child agent cannot see your conversation history unless you explicitly include relevant context in `inputs`.
</run_agent_instructions>"""


async def execute_run_agent(
    agent_name: str,
    query: str,
    inputs: Optional[Dict[str, Any]] = None,
    inherit_context: bool = True,
    max_iterations: Optional[int] = None,
) -> str:
    """占位执行函数；真实调度在状态图中完成"""
    return f"run_agent dispatch recorded for {agent_name}"


def get_run_agent_tool() -> BaseTool:
    return StructuredTool.from_function(
        name="run_agent",
        description=_run_agent_description(),
        func=None,
        coroutine=execute_run_agent,
        args_schema=RunAgentInput,
    )
