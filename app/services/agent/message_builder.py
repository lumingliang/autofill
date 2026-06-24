"""
消息构建器模块

支持构建复合消息结构，包含多种标签类型：
- <system-reminder>: 系统提醒
- <user_input>: 用户输入
- <env>: 环境信息
- <available_terminal>: 可用终端
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class EnvInfo:
    primary_working_directory: str = ""
    working_directories: List[str] = field(default_factory=list)
    operating_system: str = ""
    today_date: str = ""
    knowledge_cutoff: str = ""
    model_name: str = ""

    def to_env_text(self) -> str:
        lines = [
            "<env>",
            "You have been invoked in the following environment:",
            f"- Primary working directory: {self.primary_working_directory}",
            f"- Working directories: {', '.join(self.working_directories)}",
            f"- Operating system: {self.operating_system}",
            f"- Today's date: {self.today_date}",
            f"- Assistant knowledge cutoff is {self.knowledge_cutoff}.",
            f"- You are powered by the model named {self.model_name}.",
            "</env>"
        ]
        return "\n".join(lines)


@dataclass
class TerminalInfo:
    terminal_id: str = ""
    shell_type: str = "zsh"
    idle: bool = True
    cwd: str = ""

    def to_terminal_text(self) -> str:
        return f"- terminal_id: {self.terminal_id}, shell_type: {self.shell_type}, idle: {self.idle}, cwd: {self.cwd}"


class MessageBuilder:
    def __init__(self):
        self.env_info: Optional[EnvInfo] = None
        self.terminals: List[TerminalInfo] = []
        self.todo_reminder: Optional[str] = None
        self.skill_reminder: bool = False
        self.language_settings: bool = False
        self.tool_reminder: bool = False
        self.tool_descriptions: Optional[str] = None

    def set_env_info(self, env_info: EnvInfo) -> "MessageBuilder":
        self.env_info = env_info
        return self

    def set_terminals(self, terminals: List[TerminalInfo]) -> "MessageBuilder":
        self.terminals = terminals
        return self

    def set_todo_reminder(self, reminder: str) -> "MessageBuilder":
        self.todo_reminder = reminder
        return self

    def enable_skill_reminder(self) -> "MessageBuilder":
        self.skill_reminder = True
        return self

    def enable_language_settings(self) -> "MessageBuilder":
        self.language_settings = True
        return self

    def enable_tool_reminder(self, tool_descriptions: Optional[str] = None) -> "MessageBuilder":
        self.tool_reminder = True
        self.tool_descriptions = tool_descriptions
        return self

    def _build_terminal_reminder(self) -> Optional[str]:
        if not self.terminals:
            return None

        terminal_lines = ["<available_terminal>"]
        for term in self.terminals:
            terminal_lines.append(term.to_terminal_text())
        terminal_lines.append("</available_terminal>")

        terminal_section = "\n".join(terminal_lines)

        return f"\n<system-reminder>\n\n{terminal_section}\n\n</system-reminder>\n"

    def _build_todo_reminder(self) -> Optional[str]:
        if not self.todo_reminder:
            return None

        return f"<system-reminder>\n\n{self.todo_reminder}\n\n</system-reminder>\n"

    def _build_env_and_instructions_reminder(self) -> str:
        sections = []

        sections.append("As you answer the user's questions, you can use the following context:")

        if self.env_info:
            sections.append(self.env_info.to_env_text())

        sections.append("# important-instruction-reminders")
        sections.append("Do what has been asked; nothing more, nothing less.")
        sections.append("NEVER create files unless they're absolutely necessary for achieving your goal.")
        sections.append("ALWAYS prefer editing an existing file to creating a new one.")
        sections.append("NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.")

        content = "\n\n".join(sections)

        result = f"\n<system-reminder>\n{content}\n</system-reminder>\n"

        if self.skill_reminder:
            skill_reminder = "- Before starting any task, first review the Skill tool description to check if any skill in its <available_skills> is relevant to the <user_input> intent. When a skill is relevant, you must invoke the Skill tool IMMEDIATELY as your first action."
            result += f"\n<system-reminder>\n{skill_reminder}\n</system-reminder>\n"

        result += "\n\n\n"
        return result

    def _build_language_reminder(self) -> Optional[str]:
        if not self.language_settings:
            return None

        sections = [
            "# Response Language Settings",
            "You MUST follow these language requirements when responding to the user:",
            "- Always use the same language as the user's latest message unless user explicitly asks.",
            "- For code comments, follow the same language rule unless explicitly instructed otherwise",
            "- Maintain consistency in language throughout the conversation"
        ]

        content = "\n".join(sections)
        return f"\n<system-reminder>\n\n{content}\n</system-reminder>\n\n"

    def _build_tool_reminder(self) -> Optional[str]:
        if not self.tool_reminder:
            return None

        desc = self.tool_descriptions or "Use the available tools when needed."
        content = f"# Available Tools\n{desc}"
        return f"\n<system-reminder>\n\n{content}\n</system-reminder>\n"

    def _build_user_input_section(self, user_input: str, skill_path: Optional[str] = None, inputs: Optional[Dict[str, Any]] = None) -> str:
        user_input_content = user_input
        if inputs:
            user_input_content += f"\n\n[输入参数]: {json.dumps(inputs, ensure_ascii=False)}"

        if skill_path:
            user_input_content = f"**Skill Path:** {skill_path}\n\n{user_input_content}"

        skill_reminder = "- Before starting any task, first review the Skill tool description to check if any skill in its <available_skills> is relevant to the <user_input> intent. When a skill is relevant, you must invoke the Skill tool IMMEDIATELY as your first action."

        return f"\n<user_input>\n{user_input_content}\n</user_input>\n\n<system-reminder>\n{skill_reminder}\n</system-reminder>\n\n\n\n"

    def build_user_message(
        self,
        user_input: str,
        skill_path: Optional[str] = None,
        inputs: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        content_parts = []

        terminal_reminder = self._build_terminal_reminder()
        if terminal_reminder:
            content_parts.append({"type": "text", "text": terminal_reminder})

        todo_reminder = self._build_todo_reminder()
        if todo_reminder:
            content_parts.append({"type": "text", "text": todo_reminder})

        env_reminder = self._build_env_and_instructions_reminder()
        content_parts.append({"type": "text", "text": env_reminder})

        lang_reminder = self._build_language_reminder()
        if lang_reminder:
            content_parts.append({"type": "text", "text": lang_reminder})

        tool_reminder = self._build_tool_reminder()
        if tool_reminder:
            content_parts.append({"type": "text", "text": tool_reminder})

        user_input_section = self._build_user_input_section(user_input, skill_path, inputs)
        content_parts.append({"type": "text", "text": user_input_section})

        return content_parts
