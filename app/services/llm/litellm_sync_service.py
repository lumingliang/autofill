"""
LiteLLM 配置同步服务
负责通过 LiteLLM API 接口管理模型配置，支持双向同步
"""
from typing import Any, Dict, List

import httpx

from app.log import logger
from app.models.llm_config import LLMConfig
from app.repositories.llm.llm_config_repository import llm_config_repository
from app.settings.config import settings


class LiteLLMSyncService:
    """LiteLLM 配置同步服务 - 通过 API 接口管理"""

    def __init__(self):
        self.litellm_config = settings.LITELLM_CONFIG
        self.base_url = self.litellm_config.get("base_url", "http://localhost:4000").rstrip("/")
        self.master_key = self.litellm_config.get("master_key", "")
        self.timeout = self.litellm_config.get("timeout", 300)

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.master_key}"
        }

    def _is_masked_api_key(self, api_key: str) -> bool:
        """检查 api_key 是否为脱敏格式"""
        if not api_key:
            return False
        return "****" in api_key or "••••" in api_key or api_key.count("•") > 3

    def _build_model_payload(self, config: LLMConfig, include_model_id: bool = False) -> Dict[str, Any]:
        """
        构建 LiteLLM API 请求体

        Args:
            config: LLM 配置对象
            include_model_id: 是否包含 model_info.id（用于更新操作）

        Returns:
            API 请求体字典
        """
        # 使用 model 属性获取完整的模型名称（自动拼接 openai/ 前缀）
        model_name = config.model

        # 构建 litellm_params
        params = {
            "model": model_name,
            "timeout": config.timeout or 300
        }

        # 添加 API key（如果不是脱敏的）
        api_key = config.api_key
        if api_key and not self._is_masked_api_key(api_key):
            params["api_key"] = api_key

        # 添加可选参数
        if config.api_base:
            params["api_base"] = config.api_base

        # 构建 model_info
        model_info = {
            "mode": "chat",
            "max_tokens": 4096,
            "supports_vision": False,
            "supports_function_calling": True
        }

        # 更新操作需要包含 model_info.id
        if include_model_id and config.gateway_model_id:
            model_info["id"] = config.gateway_model_id

        # 构建请求体
        payload = {
            "model_name": config.model_id,
            "litellm_params": params,
            "model_info": model_info
        }

        return payload

    async def add_model(self, config: LLMConfig) -> tuple[bool, str]:
        """
        通过 API 添加新模型到 LiteLLM

        Args:
            config: LLM 配置对象

        Returns:
            tuple[bool, str]: (是否成功, 网关模型ID)
        """
        try:
            payload = self._build_model_payload(config)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/model/new",
                    headers=self._get_headers(),
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()

            result = response.json()
            # 从响应中提取 model_id
            model_id = result.get("model_id", "") or result.get("id", "")

            logger.info(f"Successfully added model '{config.model_id}' to LiteLLM via API, model_id={model_id}")
            return True, model_id

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to add model '{config.model_id}' to LiteLLM: HTTP {e.response.status_code} - {e.response.text}")
            return False, ""
        except Exception as e:
            logger.error(f"Failed to add model '{config.model_id}' to LiteLLM: {e}")
            return False, ""

    async def update_model(self, config: LLMConfig) -> bool:
        """
        通过 API 更新 LiteLLM 中的模型

        Args:
            config: LLM 配置对象

        Returns:
            bool: 是否成功
        """
        try:
            payload = self._build_model_payload(config, include_model_id=True)
            logger.info(f"Updating model '{config.model_id}' with payload: {payload}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/model/update",
                    headers=self._get_headers(),
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()

            logger.info(f"Successfully updated model '{config.model_id}' in LiteLLM via API")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for model '{config.model_id}': status={e.response.status_code}, response={e.response.text}")
            # 如果模型不存在（404），尝试添加
            if e.response.status_code == 404:
                logger.warning(f"Model '{config.model_id}' not found in LiteLLM, trying to add instead")
                success, model_id = await self.add_model(config)
                if success and model_id:
                    await llm_config_repository.update_gateway_model_id(config.id, model_id)
                return success
            # 如果模型在 config 文件中（400），需要先通过 /model/new 存储到数据库
            elif e.response.status_code == 400:
                error_text = e.response.text
                if "Model in config" in error_text or "Can't edit model" in error_text:
                    logger.warning(f"Model '{config.model_id}' is in config file, trying to add to DB instead")
                    success, model_id = await self.add_model(config)
                    if success and model_id:
                        await llm_config_repository.update_gateway_model_id(config.id, model_id)
                    return success
                elif "model not found" in error_text:
                    logger.warning(f"Model '{config.model_id}' not found in LiteLLM, trying to add instead")
                    success, model_id = await self.add_model(config)
                    if success and model_id:
                        await llm_config_repository.update_gateway_model_id(config.id, model_id)
                    return success
                else:
                    logger.error(f"Failed to update model '{config.model_id}' in LiteLLM: HTTP {e.response.status_code} - {error_text}")
                    return False
            logger.error(f"Failed to update model '{config.model_id}' in LiteLLM: HTTP {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Failed to update model '{config.model_id}' in LiteLLM: {e}")
            return False

    async def delete_model(self, model_name: str) -> bool:
        """
        通过 API 从 LiteLLM 删除模型

        Args:
            model_name: 模型名称

        Returns:
            bool: 是否成功
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/model/delete",
                    headers=self._get_headers(),
                    json={"id": model_name},
                    timeout=self.timeout
                )
                response.raise_for_status()

            logger.info(f"Successfully deleted model '{model_name}' from LiteLLM via API")
            return True

        except httpx.HTTPStatusError as e:
            # 如果模型不存在（404），视为成功
            if e.response.status_code == 404:
                logger.info(f"Model '{model_name}' not found in LiteLLM, already deleted")
                return True
            logger.error(f"Failed to delete model '{model_name}' from LiteLLM: HTTP {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete model '{model_name}' from LiteLLM: {e}")
            return False

    async def add_or_update_config(self, config: LLMConfig) -> bool:
        """
        添加或更新配置到 LiteLLM

        如果数据库中已有 gateway_model_id，则更新现有模型；
        否则添加新模型并保存返回的 model_id。

        Args:
            config: LLM 配置对象

        Returns:
            bool: 是否成功
        """
        if config.gateway_model_id:
            # 已有 model_id，执行更新
            return await self.update_model(config)
        else:
            # 没有 model_id，添加新模型
            success, model_id = await self.add_model(config)
            if success and model_id:
                # 保存网关返回的 model_id 到数据库
                await llm_config_repository.update_gateway_model_id(config.id, model_id)
            return success

    async def remove_config(self, model_name: str) -> bool:
        """
        从 LiteLLM 移除指定模型

        Args:
            model_name: 模型名称

        Returns:
            bool: 是否成功
        """
        return await self.delete_model(model_name)

    async def get_models_from_gateway(self) -> List[Dict[str, Any]]:
        """
        从 LiteLLM 网关获取所有模型配置

        Returns:
            List[Dict]: 模型配置列表
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/model/info",
                    headers=self._get_headers(),
                    timeout=self.timeout
                )
                response.raise_for_status()

                data = response.json()
                models = data.get("data", [])
                logger.info(f"Retrieved {len(models)} models from LiteLLM gateway")
                return models

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get models from LiteLLM: HTTP {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Failed to get models from LiteLLM: {e}")
            return []

    async def sync_from_gateway(self) -> Dict[str, Any]:
        """
        从 LiteLLM 网关同步模型配置到本地数据库

        Returns:
            Dict: 同步结果统计
        """
        result = {
            "total": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "errors": []
        }

        try:
            # 从网关获取模型列表
            gateway_models = await self.get_models_from_gateway()
            result["total"] = len(gateway_models)

            for model_data in gateway_models:
                try:
                    model_name = model_data.get("model_name", "")
                    if not model_name:
                        result["skipped"] += 1
                        continue

                    litellm_params = model_data.get("litellm_params", {})

                    # 检查本地是否已存在
                    existing = await llm_config_repository.get_by_model_id(model_id=model_name)

                    if existing:
                        # 更新现有配置（保留本地 API Key，只更新其他字段）
                        existing_api_key = existing.api_key or ""

                        # 使用网关的参数，但保留本地的 API Key
                        new_api_key = litellm_params.get("api_key", "")
                        if existing_api_key and not self._is_masked_api_key(existing_api_key):
                            new_api_key = existing_api_key
                            logger.debug(f"Preserved local API key for model '{model_name}'")

                        update_data = {
                            "api_key": new_api_key,
                            "api_base": litellm_params.get("api_base", ""),
                            "timeout": litellm_params.get("timeout", 300)
                        }
                        await llm_config_repository.update(existing.id, update_data)
                        result["updated"] += 1
                        logger.info(f"Updated model '{model_name}' from gateway (API key preserved)")
                    else:
                        # 创建新配置
                        # 从 model 字段推断提供商
                        model_provider = "openai"
                        model_value = litellm_params.get("model", "")
                        if "/" in model_value:
                            model_provider = model_value.split("/")[0]

                        # 从 model_value 中提取 model_id（去掉前缀）
                        model_id = model_value
                        if "/" in model_value:
                            model_id = model_value.split("/", 1)[1]

                        create_data = {
                            "model_id": model_name,  # 使用 model_name 作为 model_id
                            "model_provider": model_provider,
                            "api_key": litellm_params.get("api_key", ""),
                            "api_base": litellm_params.get("api_base", ""),
                            "timeout": litellm_params.get("timeout", 300),
                            "capabilities": llm_config_repository.get_default_capabilities(),
                            "is_active": True,
                            "is_default": False,
                            "description": "从 LiteLLM 网关同步导入"
                        }
                        await llm_config_repository.create(create_data)
                        result["created"] += 1
                        logger.info(f"Created new model '{model_name}' from gateway")

                except Exception as e:
                    result["failed"] += 1
                    error_msg = f"Failed to sync model '{model_data.get('model_name', 'unknown')}': {e}"
                    result["errors"].append(error_msg)
                    logger.error(error_msg)

        except Exception as e:
            error_msg = f"Failed to sync from gateway: {e}"
            result["errors"].append(error_msg)
            logger.error(error_msg)

        return result

    async def sync_all_configs(self) -> bool:
        """
        同步所有活跃的模型配置到 LiteLLM 网关
        （通过 API 逐个添加/更新）

        Returns:
            bool: 是否同步成功
        """
        try:
            # 获取所有活跃的模型配置
            configs = await llm_config_repository.get_active_configs()

            success_count = 0
            fail_count = 0

            for config in configs:
                if await self.add_or_update_config(config):
                    success_count += 1
                else:
                    fail_count += 1

            logger.info(f"Synced {success_count} models to LiteLLM, {fail_count} failed")
            return fail_count == 0

        except Exception as e:
            logger.error(f"Failed to sync configs to LiteLLM: {e}")
            return False

    async def get_gateway_health(self) -> Dict[str, Any]:
        """
        获取 LiteLLM 网关健康状态

        Returns:
            Dict: 健康状态信息
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    headers=self._get_headers(),
                    timeout=10
                )
                response.raise_for_status()

                return {
                    "status": "healthy",
                    "response": response.json()
                }

        except httpx.HTTPStatusError as e:
            return {
                "status": "unhealthy",
                "error": f"HTTP {e.response.status_code}"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# 全局服务实例
litellm_sync_service = LiteLLMSyncService()
