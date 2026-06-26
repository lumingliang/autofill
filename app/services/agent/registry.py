"""
AgentRegistry - Agent 规格注册表

支持从配置文件加载初始 Agent，也支持运行时动态注册/注销。
"""
import functools
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import ValidationError

from app.log import logger
from app.services.agent.models import AgentSpec


_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent.parent / "app" / "config" / "config.yaml"


class AgentRegistry:
    """Agent 规格注册表"""

    def __init__(self, config_path: Optional[Path] = None):
        self._agents: Dict[str, AgentSpec] = {}
        self._config_path = config_path or _DEFAULT_CONFIG_PATH
        self._load()

    def _load(self) -> None:
        if not self._config_path.exists():
            logger.warning({
                "event": "agent_config_not_found",
                "path": str(self._config_path),
            })
            return

        with open(self._config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        for agent_data in data.get("agents", []):
            try:
                spec = AgentSpec(**agent_data)
                self.register(spec)
            except ValidationError as e:
                logger.error({
                    "event": "agent_config_invalid",
                    "agent_name": agent_data.get("name"),
                    "error": str(e),
                })

        logger.info({
            "event": "agent_config_loaded",
            "path": str(self._config_path),
            "agents_count": len(self._agents),
        })

    def register(self, spec: AgentSpec) -> None:
        """注册或覆盖 Agent 规格"""
        self._agents[spec.name] = spec
        logger.info({"event": "agent_registered", "agent_name": spec.name})

    def unregister(self, name: str) -> bool:
        """注销 Agent 规格"""
        if name in self._agents:
            del self._agents[name]
            logger.info({"event": "agent_unregistered", "agent_name": name})
            return True
        return False

    def get(self, name: str) -> AgentSpec:
        """获取 Agent 规格"""
        if name not in self._agents:
            raise KeyError(f"Agent not found: {name}")
        return self._agents[name]

    def list_agents(self) -> List[AgentSpec]:
        """列出所有 Agent 规格"""
        return list(self._agents.values())

    def has(self, name: str) -> bool:
        """检查 Agent 是否存在"""
        return name in self._agents


@functools.cache
def get_agent_registry() -> AgentRegistry:
    """获取全局默认 AgentRegistry（懒加载、缓存）"""
    return AgentRegistry()
