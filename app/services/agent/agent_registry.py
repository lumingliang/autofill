"""
AgentRegistry - Agent 配置注册表

只从 app/config/config.yaml 加载，直接注册为 AgentConfig。
"""
import functools
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import ValidationError

from app.log import logger
from app.services.agent.agent_config import AgentConfig


_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent.parent / "app" / "config" / "config.yaml"


class AgentRegistry:
    """Agent 配置注册表"""

    def __init__(self, config_path: Optional[Path] = None):
        self._agents: Dict[str, AgentConfig] = {}
        self._config_path = config_path or _CONFIG_PATH
        self._load()

    def _load(self) -> None:
        if not self._config_path.exists():
            raise FileNotFoundError(f"Agent config not found: {self._config_path}")

        with open(self._config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        for agent_data in data.get("agents", []):
            try:
                config = AgentConfig(**agent_data)
                self.register(config)
            except ValidationError as e:
                logger.error({
                    "event": "agent_config_invalid",
                    "agent_name": agent_data.get("name"),
                    "error": str(e),
                })

        logger.info({
            "event": "agent_config_loaded",
            "source": str(self._config_path),
            "agents_count": len(self._agents),
        })

    def register(self, config: AgentConfig) -> None:
        """注册 Agent 配置"""
        self._agents[config.name] = config
        logger.info({"event": "agent_registered", "agent_name": config.name})

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


@functools.cache
def get_agent_registry() -> AgentRegistry:
    """获取全局默认 Agent 注册表（懒加载、缓存）"""
    return AgentRegistry()
