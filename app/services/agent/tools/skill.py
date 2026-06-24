"""
Skill 工具 - 执行技能
"""
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, ConfigDict, Field

from app.services.agent.skill_loader import load_skill, skill_loader
from app.services.agent.skill_manager import skill_manager
from app.services.agent.tool_executor import format_tool_result


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description='The skill name (no arguments). E.g., "pdf" or "xlsx"')


def _project_root() -> str:
    current_file = Path(__file__).resolve()
    # app/services/agent/tools/skill.py -> app/services/agent/tools -> app/services/agent -> app/services -> app -> project root
    return str(current_file.parent.parent.parent.parent.parent)


def _load_skills_xml(skills_base_path: Optional[str] = None) -> str:
    """从 skill 目录加载本地技能定义，生成 <available_skills> XML 片段"""
    if skills_base_path is None:
        project_root = _project_root()
        # 优先使用 .trae/skills，不存在则回退到 skill
        skills_base_path = os.path.join(project_root, ".trae", "skills")
        if not os.path.isdir(skills_base_path):
            skills_base_path = os.path.join(project_root, "skill")

    if not os.path.isdir(skills_base_path):
        return ""

    skills_xml = []
    for entry in sorted(os.listdir(skills_base_path)):
        entry_path = os.path.join(skills_base_path, entry)
        if not os.path.isdir(entry_path):
            continue
        skill_md = os.path.join(entry_path, "SKILL.md")
        if not os.path.isfile(skill_md):
            continue

        with open(skill_md, "r", encoding="utf-8") as f:
            content = f.read()

        fm_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not fm_match:
            continue

        name = None
        description = None
        for line in fm_match.group(1).split('\n'):
            line = line.strip()
            if line.startswith('name:'):
                name = line.split(':', 1)[1].strip().strip('"').strip("'")
            elif line.startswith('description:'):
                description = line.split(':', 1)[1].strip().strip('"').strip("'")

        if name and description:
            skills_xml.append(f"""<skill>
<name>
{name}
</name>
<description>
{description}
</description>
</skill>""")

    return "\n".join(skills_xml)


def _skill_description(allowed_skills: Optional[List[str]] = None) -> str:
    """生成 Skill 工具 description 段落。"""
    available_skills_xml = _load_skills_xml()
    # 如果指定了允许的技能列表，仅保留被授权的技能
    if allowed_skills:
        filtered = []
        for block in re.findall(r"<skill>\s*<name>\s*(.*?)\s*</name>\s*<description>\s*(.*?)\s*</description>\s*</skill>", available_skills_xml, re.DOTALL):
            name, description = block
            if name.strip() in allowed_skills:
                filtered.append(f"""<skill>
<name>
{name.strip()}
</name>
<description>
{description.strip()}
</description>
</skill>""")
        available_skills_xml = "\n".join(filtered)

    return f"""Execute a skill within the main conversation
<skills_instructions>
When users ask you to perform tasks, check if any of the available skills below can help complete the task more effectively. Skills provide specialized capabilities and domain knowledge.
How to use skills:
- Invoke skills using this tool with the skill name only (no arguments)
- When you invoke a skill, you will see <command-message>The "{{name}}" skill is loading</command-message>
- The skill's prompt will expand and provide detailed instructions on how to complete the task
- Examples:
  - `command: "pdf"` - invoke the pdf skill
  - `command: "xlsx"` - invoke the xlsx skill
  - `command: "ms-office-suite:pdf"` - invoke using fully qualified name
Important:
- When a skill is relevant, you must invoke this tool IMMEDIATELY as your first action
- NEVER just announce or mention a skill in your text response without actually calling this tool
- This is a BLOCKING REQUIREMENT: invoke the relevant Skill tool BEFORE generating any other response about the task
- Only use skills listed in <available_skills> below
- Do not invoke a skill that is already running
- Do not use this tool for built-in CLI commands (like /help, /clear, etc.)
</skills_instructions>
<available_skills>
{available_skills_xml}
</available_skills>"""


async def execute_skill(name: str, config: Optional[RunnableConfig] = None) -> str:
    """执行 Skill 工具"""
    if not name:
        return format_tool_result("error", {
            "type": "skill_error",
            "error": "Skill name is required. Please provide the skill name to invoke."
        })

    conversation_id = "default"
    if config and config.get("metadata"):
        context = config["metadata"].get("tool_context")
        if context:
            conversation_id = getattr(context, "session_id", "default")

    skill_config = load_skill(name)
    if skill_config:
        skill_path = os.path.join(skill_loader.skills_base_path, name, "SKILL.md")
        skill_content = skill_config.get("content", "")
        result_text = f"""**Skill Path:** {skill_path}

{skill_content}"""
        skill_manager.activate_skill(conversation_id, name)
        return format_tool_result("done", result_text, is_json=False)
    else:
        return format_tool_result("error", f"Failed to load skill: {name}", is_json=False)


def get_skill_tool(allowed_skills: Optional[List[str]] = None) -> BaseTool:
    return StructuredTool.from_function(
        name="Skill",
        description=_skill_description(allowed_skills),
        func=None,
        coroutine=execute_skill,
        args_schema=SkillInput,
    )
