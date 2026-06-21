"""
AgentRegistry - Agent 配置注册表

支持注册、查询、列出 Agent 配置；支持从 config.toml / agents.json / agents.yaml 加载。
"""
import os
from typing import Any, Dict, List, Optional

import toml
import yaml
from pydantic import ValidationError

from app.log import logger
from app.services.agent.agent_config import AgentConfig
from app.settings.config import settings


# 默认兜底 Agent 配置
_DEFAULT_AGENTS: List[Dict[str, Any]] = [
    {
        "name": "default",
        "display_name": "通用软件工程助手",
        "description": "处理通用软件工程任务",
        "system_prompt_sections": [
            "introduction",
            "system",
            "doing_tasks",
            "using_tools",
            "tone",
            "output_efficiency",
            "task_management",
            "asking_questions",
            "response_language",
            "code_reference"
        ],
        "tools": ["Skill", "Glob", "LS", "Grep", "Read", "RunCommand", "TodoWrite", "SearchReplace", "Write", "DeleteFile", "AskUserQuestion"],
        "skills": [],
        "model": "qwen3.6-plus-2026-04-02",
        "temperature": 0.7,
        "max_iterations": 10,
        "max_history": 20,
        "enable_streaming": True,
        "message_builder_options": {
            "enable_skill_reminder": True,
            "enable_language_settings": True
        }
    },
    {
        "name": "autofill",
        "display_name": "自动填单助手",
        "description": "专门处理服务记录表单自动填写",
        "system_prompt_base": "trae_base",
        "system_prompt_remove_sections": ["code_reference"],
        "system_prompt_append_sections": ["autofill_instruction"],
        "tools": ["Skill", "RunCommand", "TodoWrite", "AskUserQuestion"],
        "skills": ["autofill-form"],
        "model": "qwen3.6-plus-2026-04-02",
        "temperature": 0.7,
        "max_iterations": 20,
        "max_history": 20,
        "enable_streaming": True,
        "message_builder_options": {
            "enable_skill_reminder": True,
            "enable_language_settings": True
        }
    }
]


def _load_agents_from_toml(config_path: str = "config.toml") -> List[Dict[str, Any]]:
    """从 config.toml 加载 agents 配置"""
    if not os.path.exists(config_path):
        return []
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = toml.load(f)
        agents = config.get("agents", [])
        if isinstance(agents, dict):
            # 处理 [agents] 单表格式（未来扩展）
            agents = [agents]
        logger.info({
            "event": "agent_config_loaded",
            "source": config_path,
            "agents_count": len(agents)
        })
        return agents
    except Exception as e:
        logger.warning({"event": "agent_config_load_failed", "source": config_path, "error": str(e)})
        return []


def _load_agents_from_file(file_path: str) -> List[Dict[str, Any]]:
    """从 JSON/YAML 文件加载 agents 配置"""
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.endswith((".yaml", ".yml")):
                data = yaml.safe_load(f)
            else:
                import json
                data = json.load(f)
        agents = data if isinstance(data, list) else data.get("agents", [])
        logger.info({
            "event": "agent_config_loaded",
            "source": file_path,
            "agents_count": len(agents)
        })
        return agents
    except Exception as e:
        logger.warning({"event": "agent_config_load_failed", "source": file_path, "error": str(e)})
        return []


def _load_global_agent_defaults(config_path: str = "config.toml") -> Dict[str, Any]:
    """从 config.toml 的 [agent] 段加载全局默认配置，供默认/外部 Agent 继承"""
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = toml.load(f)
        agent_section = config.get("agent", {})
        if not isinstance(agent_section, dict):
            return {}
        # 只保留与 AgentConfig 相关的字段
        relevant_keys = {
            "model", "api_key", "base_url", "temperature", "max_iterations",
            "max_tokens", "max_history", "enable_streaming"
        }
        return {k: v for k, v in agent_section.items() if k in relevant_keys}
    except Exception as e:
        logger.warning({"event": "global_agent_config_load_failed", "error": str(e)})
        return {}


def _resolve_llm_config(agent_data: Dict[str, Any]) -> Dict[str, Any]:
    """解析 LLM 配置：未指定时 fallback 到全局 litellm 配置或环境变量"""
    litellm_config = getattr(settings, "LITELLM_CONFIG", {}) or {}

    if not agent_data.get("base_url"):
        agent_data["base_url"] = litellm_config.get("base_url") or os.getenv("OPENAI_BASE_URL", "")
    if not agent_data.get("api_key"):
        agent_data["api_key"] = litellm_config.get("master_key") or os.getenv("OPENAI_API_KEY", "")

    return agent_data


class AgentRegistry:
    """Agent 配置注册表"""

    def __init__(self):
        self._agents: Dict[str, AgentConfig] = {}
        self._global_defaults = _load_global_agent_defaults()
        self._register_default_agents()
        self._load_from_config()

    def _apply_global_defaults(self, agent_data: Dict[str, Any], is_default: bool = False) -> Dict[str, Any]:
        """将 config.toml [agent] 段的全局默认值合并到单个 Agent 配置

        对于默认 Agent：全局默认值覆盖硬编码默认值，便于统一调整。
        对于外部配置 Agent：外部显式值覆盖全局默认值，保持灵活性。
        """
        if is_default:
            # 默认 Agent：硬编码 < 全局默认值
            merged = dict(agent_data)
            merged.update(self._global_defaults)
            return merged
        # 外部配置 Agent：全局默认值 < 外部显式值
        merged = dict(self._global_defaults)
        merged.update(agent_data)
        return merged

    def _register_default_agents(self) -> None:
        """注册默认兜底 Agent"""
        for agent_data in _DEFAULT_AGENTS:
            try:
                agent_data = self._apply_global_defaults(agent_data, is_default=True)
                agent_data = _resolve_llm_config(agent_data)
                config = AgentConfig(**agent_data)
                self.register(config)
            except ValidationError as e:
                logger.error({"event": "default_agent_config_invalid", "error": str(e)})

    def _load_from_config(self) -> None:
        """从配置文件加载 Agent 配置"""
        # 加载外部配置：后加载的覆盖先加载的（agents.json/yaml > config.toml > 默认）
        sources = ["config.toml", "app/config/agents.json", "app/config/agents.yaml", "app/config/agents.yml"]
        loaded_names = set()

        for source in sources:
            if source == "config.toml":
                agents_data = _load_agents_from_toml(source)
            else:
                agents_data = _load_agents_from_file(source)

            for agent_data in agents_data:
                try:
                    agent_data = self._apply_global_defaults(agent_data, is_default=False)
                    agent_data = _resolve_llm_config(agent_data)
                    config = AgentConfig(**agent_data)
                    self.register(config)
                    loaded_names.add(config.name)
                except ValidationError as e:
                    logger.error({
                        "event": "agent_config_invalid",
                        "source": source,
                        "agent_name": agent_data.get("name"),
                        "error": str(e)
                    })

        if not loaded_names:
            logger.info({"event": "agent_config_no_external", "message": "Using default agent configurations"})

    def register(self, config: AgentConfig) -> None:
        """注册 Agent 配置"""
        self._agents[config.name] = config
        logger.info({"event": "agent_registered", "agent_name": config.name, "display_name": config.display_name})

    def get(self, name: str) -> AgentConfig:
        """获取 Agent 配置"""
        if name not in self._agents:
            raise KeyError(f"Agent not found: {name}")
        return self._agents[name]

    def list_agents(self) -> List[AgentConfig]:
        """列出所有 Agent 配置"""
        return list(self._agents.values())

    def has(self, name: str) -> bool:
        """检查 Agent 是否存在"""
        return name in self._agents


# 全局默认 Agent 注册表实例
_default_agent_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    """获取全局默认 Agent 注册表（懒加载）"""
    global _default_agent_registry
    if _default_agent_registry is None:
        _default_agent_registry = AgentRegistry()
    return _default_agent_registry
