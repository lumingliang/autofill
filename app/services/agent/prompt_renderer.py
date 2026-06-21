"""
PromptRenderer - 系统提示词渲染器

按章节列表加载提示词片段、替换占位符、拼接为完整系统提示词。
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.log import logger
from app.services.agent.prompt_sections import SECTIONS


class PromptRenderer:
    """提示词渲染器"""

    def __init__(self, sections_dir: Optional[str] = None, templates_path: Optional[str] = None):
        if sections_dir is None:
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            sections_dir = os.path.join(project_root, "app", "config", "agent_prompts", "sections")
        self.sections_dir = sections_dir

        if templates_path is None:
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            templates_path = os.path.join(project_root, "app", "config", "agent_prompts", "templates.json")
        self.templates_path = templates_path
        self._templates: Optional[Dict[str, Any]] = None

    def _load_templates(self) -> Dict[str, Any]:
        """加载模板定义"""
        if self._templates is None:
            if os.path.exists(self.templates_path):
                try:
                    with open(self.templates_path, "r", encoding="utf-8") as f:
                        self._templates = json.load(f)
                    logger.info({
                        "event": "prompt_templates_loaded",
                        "templates_path": self.templates_path,
                        "templates_count": len(self._templates)
                    })
                except Exception as e:
                    logger.warning({
                        "event": "prompt_templates_load_failed",
                        "templates_path": self.templates_path,
                        "error": str(e)
                    })
                    self._templates = {}
            else:
                self._templates = {}
        return self._templates

    def load_section(self, section_name: str) -> str:
        """加载单个章节内容

        优先级：配置文件目录 > Python 默认 > 空字符串
        """
        file_path = os.path.join(self.sections_dir, f"{section_name}.md")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                logger.debug({"event": "prompt_section_loaded", "section": section_name, "source": "file"})
                return content
            except Exception as e:
                logger.warning({"event": "prompt_section_load_failed", "section": section_name, "error": str(e)})

        if section_name in SECTIONS:
            logger.debug({"event": "prompt_section_loaded", "section": section_name, "source": "fallback"})
            return SECTIONS[section_name]

        logger.warning({"event": "prompt_section_missing", "section": section_name})
        return ""

    def render_text(self, template_text: str, variables: Dict[str, Any]) -> str:
        """渲染单个文本模板，替换占位符"""
        result = template_text
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result

    def resolve_sections(
        self,
        sections: Optional[List[str]] = None,
        base: Optional[str] = None,
        remove_sections: Optional[List[str]] = None,
        append_sections: Optional[List[str]] = None,
    ) -> List[str]:
        """解析最终章节列表"""
        if sections is not None:
            return list(sections)

        templates = self._load_templates()
        resolved: List[str] = []

        if base and base in templates:
            base_sections = templates[base].get("sections", [])
            resolved = list(base_sections)
        elif base:
            logger.warning({"event": "prompt_template_base_not_found", "base": base})

        if remove_sections:
            resolved = [s for s in resolved if s not in remove_sections]

        if append_sections:
            resolved = resolved + [s for s in append_sections if s not in resolved]

        return resolved

    def render(
        self,
        sections: Optional[List[str]] = None,
        variables: Optional[Dict[str, Any]] = None,
        separator: str = "\n\n",
        base: Optional[str] = None,
        remove_sections: Optional[List[str]] = None,
        append_sections: Optional[List[str]] = None,
    ) -> str:
        """渲染完整系统提示词"""
        variables = variables or {}

        # 默认注入当前日期
        if "current_date" not in variables:
            variables["current_date"] = datetime.now().strftime("%Y-%m-%d")

        final_sections = self.resolve_sections(
            sections=sections,
            base=base,
            remove_sections=remove_sections,
            append_sections=append_sections,
        )

        parts = []
        for section_name in final_sections:
            content = self.load_section(section_name)
            if content:
                parts.append(self.render_text(content, variables))

        # 使用分隔符拼接，确保每个章节末尾已有分隔符时不重复添加
        result = ""
        for i, part in enumerate(parts):
            if i > 0:
                if not result.endswith(separator) and not part.startswith(separator):
                    result += separator
                elif result.endswith(separator) and part.startswith(separator):
                    result = result[: -len(separator)]
            result += part

        # 对未替换的占位符做兜底处理（保留原样，避免 format 报错）
        return result


# 全局默认渲染器实例
_default_prompt_renderer: Optional[PromptRenderer] = None


def get_prompt_renderer() -> PromptRenderer:
    """获取全局默认提示词渲染器（懒加载）"""
    global _default_prompt_renderer
    if _default_prompt_renderer is None:
        _default_prompt_renderer = PromptRenderer()
    return _default_prompt_renderer
