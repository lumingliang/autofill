"""
Skill 加载器模块 - 实现 Skill 的加载和执行

Skill 目录结构：
{agent_base_dir}/skills/{skill-name}/SKILL.md

支持多个 agent base dir，按优先级合并（前面的目录覆盖后面的目录）。
"""
import os
import re
import json
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from app.log import logger
from app.settings.config import settings


def _project_root() -> str:
    current_file = Path(__file__).resolve()
    # app/services/agent/skill_loader.py -> app/services/agent -> app/services -> app -> project root
    return str(current_file.parent.parent.parent.parent)


def _default_skills_base_paths() -> List[str]:
    """根据配置生成默认的 skills 基础路径列表（优先级从高到低）。"""
    project_root = _project_root()
    base_dirs = settings.AGENT_BASE_DIR if isinstance(settings.AGENT_BASE_DIR, list) else [settings.AGENT_BASE_DIR]
    return [os.path.join(project_root, base_dir, "skills") for base_dir in base_dirs]


class SkillLoader:
    """Skill 加载器"""

    def __init__(self, skills_base_path: Union[str, List[str], None] = None):
        if skills_base_path is None:
            self._skills_base_paths = _default_skills_base_paths()
        elif isinstance(skills_base_path, str):
            self._skills_base_paths = [skills_base_path]
        else:
            self._skills_base_paths = list(skills_base_path)

        self._loaded_skills: Dict[str, Dict[str, Any]] = {}

    @property
    def skills_base_path(self) -> str:
        """返回最高优先级的 skills 基础路径（兼容旧代码）。"""
        return self._skills_base_paths[0] if self._skills_base_paths else ""

    def _find_skill_path(self, skill_name: str) -> Optional[str]:
        """在所有基础路径中按优先级查找 SKILL.md 文件。"""
        for base_path in self._skills_base_paths:
            skill_path = os.path.join(base_path, skill_name, "SKILL.md")
            if os.path.exists(skill_path):
                return skill_path
        return None

    def load_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """
        加载指定的 Skill

        Args:
            skill_name: Skill 名称

        Returns:
            Skill 配置字典，如果加载失败返回 None
        """
        # 检查缓存
        if skill_name in self._loaded_skills:
            return self._loaded_skills[skill_name]

        skill_path = self._find_skill_path(skill_name)

        if not skill_path:
            logger.warning({
                "event": "skill_load_not_found",
                "skill_name": skill_name,
                "skills_base_paths": self._skills_base_paths,
            })
            return None

        try:
            with open(skill_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析 Skill 内容
            skill_config = self._parse_skill_md(content, skill_name)
            self._loaded_skills[skill_name] = skill_config

            logger.info({
                "event": "skill_load_success",
                "skill_name": skill_name,
                "skill_path": skill_path,
            })

            return skill_config

        except Exception as e:
            logger.error({
                "event": "skill_load_failed",
                "skill_name": skill_name,
                "skill_path": skill_path,
                "error": str(e),
            })
            return None

    def _parse_skill_md(self, content: str, skill_name: str) -> Dict[str, Any]:
        """解析 Skill Markdown 文件"""
        config = {
            "name": skill_name,
            "description": "",
            "content": content,
            "workflow": [],
            "cli_scripts": {},
            "examples": []
        }

        # 提取 frontmatter
        frontmatter_match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)
            # 解析 name 和 description
            name_match = re.search(r'name:\s*"?([^"\n]+)"?', frontmatter)
            if name_match:
                config["name"] = name_match.group(1).strip()

            desc_match = re.search(r'description:\s*"?([^"\n]+)"?', frontmatter)
            if desc_match:
                config["description"] = desc_match.group(1).strip()

        # 提取 CLI 脚本路径
        cli_pattern = r'`{0,3}(?:bash)?\s*\n?(python\s+\S+\.py)'
        cli_matches = re.findall(cli_pattern, content)
        for i, cli in enumerate(cli_matches):
            config["cli_scripts"][f"step_{i+1}"] = cli.strip()

        # 提取工作流步骤
        workflow_pattern = r'步骤(\d+):\s*([^\n]+)'
        workflow_matches = re.findall(workflow_pattern, content)
        for step_num, step_desc in workflow_matches:
            config["workflow"].append({
                "step": int(step_num),
                "description": step_desc.strip()
            })

        return config

    def get_skill_prompt(self, skill_name: str) -> Optional[str]:
        """获取 Skill 的完整提示词"""
        skill = self.load_skill(skill_name)
        if skill:
            return skill["content"]
        return None

    def list_available_skills(self) -> list:
        """列出所有可用的 Skills（多目录合并，高优先级覆盖低优先级）。"""
        skills_map: Dict[str, Dict[str, Any]] = {}

        for base_path in self._skills_base_paths:
            if not os.path.exists(base_path):
                logger.warning({
                    "event": "skill_list_no_directory",
                    "skills_base_path": base_path,
                })
                continue

            for item in os.listdir(base_path):
                skill_path = os.path.join(base_path, item)
                skill_md = os.path.join(skill_path, "SKILL.md")

                if os.path.isdir(skill_path) and os.path.exists(skill_md):
                    skill_config = self.load_skill(item)
                    if skill_config:
                        # 高优先级目录已加载的技能会覆盖低优先级的
                        skills_map[skill_config["name"]] = {
                            "name": skill_config["name"],
                            "description": skill_config["description"],
                        }

        skills = list(skills_map.values())
        logger.info({
            "event": "skill_list_complete",
            "skills_count": len(skills),
            "skills": [s["name"] for s in skills],
        })

        return skills


# 全局 Skill 加载器实例
skill_loader = SkillLoader()


def load_skill(skill_name: str) -> Optional[Dict[str, Any]]:
    """加载指定的 Skill"""
    return skill_loader.load_skill(skill_name)


def get_skill_prompt(skill_name: str) -> Optional[str]:
    """获取 Skill 的提示词"""
    return skill_loader.get_skill_prompt(skill_name)


def list_skills() -> list:
    """列出所有可用的 Skills"""
    return skill_loader.list_available_skills()
