"""
Skill 管理器 - 跟踪当前会话中激活的 Skill
"""
from typing import Any, Dict, Optional

from app.services.agent.skill_loader import load_skill


class SkillManager:
    """Skill 管理器 - 管理会话内 Skill 激活状态"""

    def __init__(self):
        self._active_skills: Dict[str, Dict[str, Any]] = {}  # conversation_id -> skill context

    def activate_skill(self, conversation_id: str, skill_name: str) -> bool:
        """激活指定的 Skill"""
        skill_config = load_skill(skill_name)
        if skill_config:
            self._active_skills[conversation_id] = {
                "name": skill_name,
                "config": skill_config,
                "step": 0,
                "data": {}
            }
            return True
        return False

    def get_active_skill(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """获取当前激活的 Skill"""
        return self._active_skills.get(conversation_id)

    def is_skill_active(self, conversation_id: str) -> bool:
        """检查是否有 Skill 处于激活状态"""
        return conversation_id in self._active_skills

    def deactivate_skill(self, conversation_id: str):
        """停用 Skill"""
        if conversation_id in self._active_skills:
            del self._active_skills[conversation_id]

    def get_skill_system_prompt(self, conversation_id: str) -> Optional[str]:
        """获取当前 Skill 的系统提示词"""
        skill_ctx = self._active_skills.get(conversation_id)
        if skill_ctx:
            return skill_ctx["config"]["content"]
        return None


# 全局 Skill 管理器实例
skill_manager = SkillManager()
