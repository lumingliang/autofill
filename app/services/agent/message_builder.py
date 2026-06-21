"""
消息构建器模块 - 严格遵循 1.json 规范

支持构建复合消息结构，包含多种标签类型：
- <system-reminder>: 系统提醒
- <user_input>: 用户输入
- <env>: 环境信息
- <available_terminal>: 可用终端

1.json 中的 User 消息格式：
{
  "role": "user",
  "content": [
    {"type": "text", "text": "\n<system-reminder>\n\n<available_terminal>...</available_terminal>\n\n</system-reminder>\n"},
    {"type": "text", "text": "<system-reminder>\n\nThis is a reminder that your todo list...\n\n</system-reminder>\n"},
    {"type": "text", "text": "\n<system-reminder>\n<env>...</env>\n\n# important-instruction-reminders\n...\n</system-reminder>\n\n<system-reminder>\n- Before starting any task...\n</system-reminder>\n\n\n"},
    {"type": "text", "text": "\n<system-reminder>\n\n# Response Language Settings\n...\n</system-reminder>\n"},
    {"type": "text", "text": "\n<user_input>\n用户输入\n</user_input>\n\n<system-reminder>\n- Before starting any task...\n</system-reminder>\n\n\n"}
  ]
}
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class EnvInfo:
    """环境信息 - 对应 1.json 中的 <env>"""
    primary_working_directory: str = ""
    working_directories: List[str] = field(default_factory=list)
    operating_system: str = ""
    today_date: str = ""
    knowledge_cutoff: str = ""
    model_name: str = ""

    def to_env_text(self) -> str:
        """生成 <env> 标签内容"""
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
    """终端信息 - 对应 1.json 中的 <available_terminal>"""
    terminal_id: str = ""
    shell_type: str = "zsh"
    idle: bool = True
    cwd: str = ""

    def to_terminal_text(self) -> str:
        """生成终端列表文本"""
        return f"- terminal_id: {self.terminal_id}, shell_type: {self.shell_type}, idle: {self.idle}, cwd: {self.cwd}"


class MessageBuilder:
    """
    消息构建器 - 严格按照 1.json 格式构建复合消息
    """

    def __init__(self):
        self.env_info: Optional[EnvInfo] = None
        self.terminals: List[TerminalInfo] = []
        self.todo_reminder: Optional[str] = None
        self.skill_reminder: bool = False
        self.language_settings: bool = False
        self.tool_reminder: bool = False
        self.tool_descriptions: Optional[str] = None

    def set_env_info(self, env_info: EnvInfo) -> "MessageBuilder":
        """设置环境信息"""
        self.env_info = env_info
        return self

    def set_terminals(self, terminals: List[TerminalInfo]) -> "MessageBuilder":
        """设置可用终端列表"""
        self.terminals = terminals
        return self

    def set_todo_reminder(self, reminder: str) -> "MessageBuilder":
        """设置 Todo 提醒"""
        self.todo_reminder = reminder
        return self

    def enable_skill_reminder(self) -> "MessageBuilder":
        """启用 Skill 触发提醒"""
        self.skill_reminder = True
        return self

    def enable_language_settings(self) -> "MessageBuilder":
        """启用语言设置提醒"""
        self.language_settings = True
        return self

    def enable_tool_reminder(self, tool_descriptions: Optional[str] = None) -> "MessageBuilder":
        """启用工具说明提醒"""
        self.tool_reminder = True
        self.tool_descriptions = tool_descriptions
        return self

    def _build_terminal_reminder(self) -> Optional[str]:
        """构建终端信息 reminder - 对应 1.json 第一个 content 元素"""
        if not self.terminals:
            return None

        terminal_lines = ["<available_terminal>"]
        for term in self.terminals:
            terminal_lines.append(term.to_terminal_text())
        terminal_lines.append("</available_terminal>")

        terminal_section = "\n".join(terminal_lines)

        return f"\n<system-reminder>\n\n{terminal_section}\n\n</system-reminder>\n"

    def _build_todo_reminder(self) -> Optional[str]:
        """构建 Todo reminder - 对应 1.json 第二个 content 元素"""
        if not self.todo_reminder:
            return None

        return f"<system-reminder>\n\n{self.todo_reminder}\n\n</system-reminder>\n"

    def _build_env_and_instructions_reminder(self) -> str:
        """构建环境信息和重要指令 reminder - 对应 1.json 第三个 content 元素"""
        sections = []

        # <env> 部分
        if self.env_info:
            sections.append(self.env_info.to_env_text())

        # 重要指令提醒
        sections.append("# important-instruction-reminders")
        sections.append("Do what has been asked; nothing more, nothing less.")
        sections.append("NEVER create files unless they're absolutely necessary for achieving your goal.")
        sections.append("ALWAYS prefer editing an existing file to creating a new one.")
        sections.append("NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.")

        # Skill 触发提醒
        if self.skill_reminder:
            sections.append("- Before starting any task, first review the Skill tool description to check if any skill in its <available_skills> is relevant to the <user_input> intent. When a skill is relevant, you must invoke the Skill tool IMMEDIATELY as your first action.")

        content = "\n\n".join(sections)

        # 注意：这里有两个 system-reminder，第二个是 Skill 提醒
        skill_reminder = "- Before starting any task, first review the Skill tool description to check if any skill in its <available_skills> is relevant to the <user_input> intent. When a skill is relevant, you must invoke the Skill tool IMMEDIATELY as your first action."

        return f"\n<system-reminder>\n{content}\n</system-reminder>\n\n<system-reminder>\n{skill_reminder}\n</system-reminder>\n\n\n"

    def _build_language_reminder(self) -> Optional[str]:
        """构建语言设置 reminder - 对应 1.json 第四个 content 元素"""
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
        return f"\n<system-reminder>\n\n{content}\n</system-reminder>\n"

    def _build_tool_reminder(self) -> Optional[str]:
        """构建工具说明 reminder"""
        if not self.tool_reminder:
            return None

        desc = self.tool_descriptions or "Use the available tools when needed."
        content = f"# Available Tools\n{desc}"
        return f"\n<system-reminder>\n\n{content}\n</system-reminder>\n"

    def _build_user_input_section(self, user_input: str, skill_path: Optional[str] = None, inputs: Optional[Dict[str, Any]] = None) -> str:
        """构建用户输入 section - 对应 1.json 第五个 content 元素"""
        # 构建用户输入内容
        user_input_content = user_input
        if inputs:
            user_input_content += f"\n\n[输入参数]: {json.dumps(inputs, ensure_ascii=False)}"

        # 添加 Skill 路径（如果有）
        if skill_path:
            user_input_content = f"**Skill Path:** {skill_path}\n\n{user_input_content}"

        # Skill 触发提醒（在 user_input 后面）
        skill_reminder = "- Before starting any task, first review the Skill tool description to check if any skill in its <available_skills> is relevant to the <user_input> intent. When a skill is relevant, you must invoke the Skill tool IMMEDIATELY as your first action."

        return f"\n<user_input>\n{user_input_content}\n</user_input>\n\n<system-reminder>\n{skill_reminder}\n</system-reminder>\n\n\n"

    def build_user_message(
        self,
        user_input: str,
        skill_path: Optional[str] = None,
        inputs: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """
        构建完整的用户消息（复合结构）- 严格按照 1.json 格式

        Args:
            user_input: 用户输入内容
            skill_path: 可选的 Skill 路径
            inputs: 可选的输入参数

        Returns:
            content 数组，每个元素是 {"type": "text", "text": "..."}
        """
        content_parts = []

        # 1. 终端信息 reminder
        terminal_reminder = self._build_terminal_reminder()
        if terminal_reminder:
            content_parts.append({"type": "text", "text": terminal_reminder})

        # 2. Todo reminder
        todo_reminder = self._build_todo_reminder()
        if todo_reminder:
            content_parts.append({"type": "text", "text": todo_reminder})

        # 3. 环境信息和重要指令 reminder
        env_reminder = self._build_env_and_instructions_reminder()
        content_parts.append({"type": "text", "text": env_reminder})

        # 4. 语言设置 reminder
        lang_reminder = self._build_language_reminder()
        if lang_reminder:
            content_parts.append({"type": "text", "text": lang_reminder})

        # 5. 工具说明 reminder（可选）
        tool_reminder = self._build_tool_reminder()
        if tool_reminder:
            content_parts.append({"type": "text", "text": tool_reminder})

        # 6. 用户输入
        user_input_section = self._build_user_input_section(user_input, skill_path, inputs)
        content_parts.append({"type": "text", "text": user_input_section})

        return content_parts

    def build_simple_user_message(self, user_input: str) -> List[Dict[str, str]]:
        """
        构建简单的用户消息（最小化结构）

        Args:
            user_input: 用户输入内容

        Returns:
            content 数组
        """
        skill_reminder = "- Before starting any task, first review the Skill tool description to check if any skill in its <available_skills> is relevant to the <user_input> intent. When a skill is relevant, you must invoke the Skill tool IMMEDIATELY as your first action."

        return [
            {
                "type": "text",
                "text": f"<system-reminder>\n{skill_reminder}\n</system-reminder>\n"
            },
            {
                "type": "text",
                "text": f"<user_input>\n{user_input}\n</user_input>\n\n<system-reminder>\n{skill_reminder}\n</system-reminder>\n"
            }
        ]


# 全局消息构建器实例
def get_message_builder() -> MessageBuilder:
    """获取消息构建器实例"""
    return MessageBuilder()
