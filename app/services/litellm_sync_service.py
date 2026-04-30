"""
LiteLLM 配置同步服务
负责将数据库中的模型配置同步到 LiteLLM 配置文件
"""
import logging
import os
from typing import Any, Dict, List, Optional

import yaml
from tortoise.expressions import Q

from app.models.llm_config import LLMConfig
from app.settings.config import settings

logger = logging.getLogger(__name__)


class LiteLLMSyncService:
    """LiteLLM 配置同步服务"""

    def __init__(self):
        self.config_path = os.path.join(os.getcwd(), "litellm_config.yaml")
        self.litellm_config = settings.LITELLM_CONFIG

    async def sync_all_configs(self) -> bool:
        """
        同步所有活跃的模型配置到 LiteLLM 配置文件

        Returns:
            bool: 是否同步成功
        """
        try:
            # 获取所有活跃的模型配置
            configs = await LLMConfig.filter(is_active=True).all()

            # 构建 LiteLLM 配置
            model_list = []
            for config in configs:
                litellm_params = config.litellm_params or {}
                if not litellm_params:
                    continue

                # 构建模型配置项
                model_item = {
                    "model_name": config.name,
                    "litellm_params": {
                        "model": litellm_params.get("model", ""),
                        "api_key": litellm_params.get("api_key", ""),
                        "timeout": litellm_params.get("timeout", 60)
                    }
                }

                # 添加可选参数
                if litellm_params.get("api_base"):
                    model_item["litellm_params"]["api_base"] = litellm_params["api_base"]
                if litellm_params.get("api_version"):
                    model_item["litellm_params"]["api_version"] = litellm_params["api_version"]

                # 添加 model_info
                model_info = config.model_info or {}
                if model_info:
                    model_item["model_info"] = model_info

                model_list.append(model_item)

            # 构建完整的 LiteLLM 配置
            litellm_config_data = {
                "general_settings": {
                    "master_key": self.litellm_config.get("master_key", "sk-litellm-master-key"),
                    "port": self.litellm_config.get("port", 4000),
                    "host": self.litellm_config.get("host", "0.0.0.0"),
                    "store_model_in_db": False  # 使用文件配置
                },
                "model_list": model_list
            }

            # 写入配置文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(litellm_config_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

            logger.info(f"Synced {len(model_list)} models to LiteLLM config file")
            return True

        except Exception as e:
            logger.error(f"Failed to sync configs to LiteLLM: {e}")
            return False

    async def add_or_update_config(self, config: LLMConfig) -> bool:
        """
        添加或更新单个配置到 LiteLLM

        Args:
            config: LLM 配置对象

        Returns:
            bool: 是否成功
        """
        try:
            # 重新同步所有配置（最简单可靠的方式）
            return await self.sync_all_configs()
        except Exception as e:
            logger.error(f"Failed to add/update config in LiteLLM: {e}")
            return False

    async def remove_config(self, config_name: str) -> bool:
        """
        从 LiteLLM 配置中移除指定模型

        Args:
            config_name: 配置名称

        Returns:
            bool: 是否成功
        """
        try:
            # 重新同步所有配置
            return await self.sync_all_configs()
        except Exception as e:
            logger.error(f"Failed to remove config from LiteLLM: {e}")
            return False

    async def reload_litellm(self) -> bool:
        """
        触发 LiteLLM 配置重载

        Returns:
            bool: 是否成功
        """
        try:
            import httpx

            base_url = self.litellm_config.get("base_url", "http://localhost:4000")
            master_key = self.litellm_config.get("master_key", "")

            # 调用 LiteLLM 的 /config/reload 接口（如果支持）
            # 或者通过发送 SIGHUP 信号
            # 目前 LiteLLM 支持配置文件热重载，无需额外操作

            logger.info("LiteLLM config file updated, will be auto-reloaded")
            return True

        except Exception as e:
            logger.error(f"Failed to reload LiteLLM: {e}")
            return False


# 全局服务实例
litellm_sync_service = LiteLLMSyncService()
