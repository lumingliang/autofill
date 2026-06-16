"""
Skill 加载器模块 - 实现 Skill 的加载和执行

Skill 目录结构：
.trae/skills/{skill-name}/SKILL.md
"""
import os
import re
import json
from typing import Dict, Any, Optional
from pathlib import Path


class SkillLoader:
    """Skill 加载器"""

    def __init__(self, skills_base_path: str = None):
        if skills_base_path is None:
            # 默认从项目根目录的 .trae/skills 加载
            # 从当前文件位置向上回溯: app/services/agent/skill_loader.py -> 项目根目录
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent.parent
            skills_base_path = os.path.join(project_root, ".trae", "skills")

        self.skills_base_path = skills_base_path
        self._loaded_skills: Dict[str, Dict[str, Any]] = {}
    
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
        
        # 构建 Skill 路径
        skill_path = os.path.join(self.skills_base_path, skill_name, "SKILL.md")
        
        if not os.path.exists(skill_path):
            return None
        
        try:
            with open(skill_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析 Skill 内容
            skill_config = self._parse_skill_md(content, skill_name)
            self._loaded_skills[skill_name] = skill_config
            
            return skill_config
            
        except Exception as e:
            print(f"加载 Skill {skill_name} 失败: {e}")
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
        """列出所有可用的 Skills"""
        skills = []
        
        if not os.path.exists(self.skills_base_path):
            return skills
        
        for item in os.listdir(self.skills_base_path):
            skill_path = os.path.join(self.skills_base_path, item)
            skill_md = os.path.join(skill_path, "SKILL.md")
            
            if os.path.isdir(skill_path) and os.path.exists(skill_md):
                skill_config = self.load_skill(item)
                if skill_config:
                    skills.append({
                        "name": skill_config["name"],
                        "description": skill_config["description"]
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
