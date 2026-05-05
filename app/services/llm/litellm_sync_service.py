"""
LiteLLM 配置同步服务
负责将数据库中的模型配置同步到 LiteLLM 配置文件
"""
import os
from typing import Any, Dict, List, Optional

import httpx
import yaml
from tortoise.expressions import Q

from app.log import logger
from app.models.llm_config import LLMConfig
from app.settings.config import settings


class LiteLLMSyncService:
    """LiteLLM 配置同步服务"""

    def __init__(self):
        # LiteLLM 网关实际使用的配置文件是 config.yaml
        self.config_path = os.path.join(settings.BASE_DIR, "litellm", "config.yaml")
        self.litellm_config = settings.LITELLM_CONFIG

    def _is_masked_api_key(self, api_key: str) -> bool:
        """检查 api_key 是否为脱敏格式"""
        if not api_key:
            return False
        # 脱敏格式示例: ms-9****f738, sk-abc****xyz, ••••••••••••
        return '****' in api_key or '••••' in api_key or api_key.count('•') > 3

    async def sync_all_configs(self) -> bool:
        """
        同步所有活跃的模型配置到 LiteLLM 配置文件

        Returns:
            bool: 是否同步成功
        """
        try:
            # 读取现有的配置文件（用于保留正确的 API key）
            existing_configs = {}
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        existing_data = yaml.safe_load(f)
                        if existing_data and 'model_list' in existing_data:
                            for item in existing_data['model_list']:
                                model_name = item.get('model_name')
                                if model_name:
                                    existing_configs[model_name] = item
                except Exception as e:
                    logger.warning(f"Failed to read existing config: {e}")

            # 获取所有活跃的模型配置
            configs = await LLMConfig.filter(is_active=True).all()

            # 构建 LiteLLM 配置
            model_list = []
            for config in configs:
                litellm_params = config.litellm_params or {}
                if not litellm_params:
                    continue

                # 获取 API key
                api_key = litellm_params.get("api_key", "")

                # 如果 API key 被脱敏，尝试从现有配置中恢复
                if self._is_masked_api_key(api_key):
                    existing_config = existing_configs.get(config.name, {})
                    existing_params = existing_config.get('litellm_params', {})
                    existing_api_key = existing_params.get('api_key', '')
                    if existing_api_key and not self._is_masked_api_key(existing_api_key):
                        api_key = existing_api_key
                        logger.info(f"Restored API key for model {config.name} from existing config")
                    else:
                        logger.warning(f"API key for model {config.name} is masked and no valid key found in existing config")

                # 处理模型名称：如果是 OpenAI 提供商且模型名称没有 openai/ 前缀，自动添加
                model_name = litellm_params.get("model", "")
                if config.model_provider == "openai" and model_name and not model_name.startswith("openai/"):
                    model_name = f"openai/{model_name}"
                    logger.info(f"Auto-added 'openai/' prefix for model {config.name}: {model_name}")

                # 构建模型配置项
                model_item = {
                    "model_name": config.name,
                    "litellm_params": {
                        "model": model_name,
                        "api_key": api_key,
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
