"""
LLM 配置 Service 层

处理 LLM 配置相关的业务逻辑，包括：
- LLM 配置的 CRUD 操作
- 配置同步到 LiteLLM 网关
- 配置测试

约束：
- 使用 @atomic() 装饰器控制事务
- 不直接查询 Model 层，通过 Repository 层访问数据
"""
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import HTTPException
from tortoise.expressions import Q
from tortoise.transactions import atomic

from app.log import logger
from app.models.llm_config import LLMConfig
from app.repositories.llm.llm_config_repository import llm_config_repository
from app.services.llm.litellm_sync_service import litellm_sync_service
from app.settings.config import settings


class LLMConfigService:
    """
    LLM 配置 Service

    职责：
    - 处理 LLM 配置的业务逻辑
    - 管理配置同步到 LiteLLM 网关
    - 调用 Repository 层进行数据操作

    约束：
    - 使用 @atomic() 装饰器控制事务
    - 不直接操作数据库，通过 Repository 层访问数据
    """

    async def get_by_id(self, id: int) -> LLMConfig:
        """根据ID获取配置"""
        config = await llm_config_repository.get_by_id(id)
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在")
        return config

    async def list_configs(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Q = None,
        order: List[str] = None
    ) -> Tuple[int, List[LLMConfig]]:
        """
        获取配置列表

        Args:
            page: 页码
            page_size: 每页数量
            search: 查询条件
            order: 排序字段

        Returns:
            Tuple[int, List[LLMConfig]]: (总数, 配置列表)
        """
        if order is None:
            order = ["-updated_at"]

        total, configs = await llm_config_repository.list(
            page=page,
            page_size=page_size,
            search=search,
            order=order
        )
        return total, configs

    @atomic()
    async def create_config(self, model_id: str, model_provider: str,
                           api_key: str = "", api_base: str = "", timeout: int = 300,
                           is_default: bool = False, is_active: bool = True,
                           description: str = "", **kwargs) -> LLMConfig:
        """
        创建 LLM 配置

        Args:
            model_id: Model ID
            model_provider: 模型提供商
            api_key: API密钥
            api_base: API基础URL
            timeout: 超时时间
            is_default: 是否为默认配置
            is_active: 是否启用
            description: 描述

        Returns:
            LLMConfig: 创建的配置
        """
        # 检查 model_id 是否已存在
        existing = await llm_config_repository.get_by_model_id(model_id)
        if existing:
            raise HTTPException(status_code=400, detail="已存在相同的 Model ID")

        # 准备数据
        create_data = {
            "model_id": model_id,
            "model_provider": model_provider,
            "api_key": api_key,
            "api_base": api_base,
            "timeout": timeout,
            "is_default": is_default,
            "is_active": is_active,
            "description": description,
            "capabilities": llm_config_repository.get_default_capabilities()
        }
        create_data.update(kwargs)

        # 如果设置为默认配置，取消其他默认配置
        if is_default:
            default_config = await llm_config_repository.get_default_config()
            if default_config:
                await llm_config_repository.update(default_config.id, {"is_default": False})

        # 创建配置
        config = await llm_config_repository.create(create_data)

        # 同步到 LiteLLM 网关
        await self._sync_to_litellm(config, action="create")

        return config

    @atomic()
    async def update_config(
        self,
        id: int,
        model_id: str = None,
        model_provider: str = None,
        api_key: str = None,
        api_base: str = None,
        timeout: int = None,
        is_default: bool = None,
        is_active: bool = None,
        description: str = None,
        **kwargs
    ) -> LLMConfig:
        """
        更新 LLM 配置

        Args:
            id: 配置ID
            ...其他字段

        Returns:
            LLMConfig: 更新后的配置
        """
        config = await self.get_by_id(id)

        # 如果修改了 model_id，检查唯一性
        if model_id and model_id != config.model_id:
            existing = await llm_config_repository.get_by_model_id(model_id)
            if existing and existing.id != id:
                raise HTTPException(status_code=400, detail="已存在相同的 Model ID")

        # 准备更新数据
        update_data = {}
        if model_id is not None:
            update_data["model_id"] = model_id
        if model_provider is not None:
            update_data["model_provider"] = model_provider
        if api_key is not None:
            # 检查 api_key 是否被脱敏
            if not self._is_masked_api_key(api_key):
                update_data["api_key"] = api_key
        if api_base is not None:
            update_data["api_base"] = api_base
        if timeout is not None:
            update_data["timeout"] = timeout
        if is_active is not None:
            update_data["is_active"] = is_active
        if description is not None:
            update_data["description"] = description

        # 如果设置为默认配置，取消其他默认配置
        if is_default:
            default_config = await llm_config_repository.get_default_config()
            if default_config and default_config.id != id:
                await llm_config_repository.update(default_config.id, {"is_default": False})
            update_data["is_default"] = True

        update_data.update(kwargs)

        # 更新配置
        updated = await llm_config_repository.update(id, update_data)

        # 同步到 LiteLLM 网关
        await self._sync_to_litellm(updated, action="update")

        return updated

    @atomic()
    async def delete_config(self, id: int) -> None:
        """
        删除 LLM 配置

        Args:
            id: 配置ID
        """
        config = await self.get_by_id(id)

        # 从 LiteLLM 网关移除
        await self._sync_to_litellm(config, action="delete")

        # 删除配置
        await llm_config_repository.delete(id)

    def _is_masked_api_key(self, api_key: str) -> bool:
        """检查 api_key 是否为脱敏格式"""
        if not api_key:
            return False
        return '****' in api_key or '••••' in api_key or api_key.count('•') > 3

    async def _sync_to_litellm(self, config: LLMConfig, action: str = "create"):
        """同步配置到 LiteLLM 网关"""
        try:
            if action in ["create", "update"]:
                await litellm_sync_service.add_or_update_config(config)
            elif action == "delete":
                await litellm_sync_service.remove_config(config.model_id)
        except Exception as e:
            logger.warning(f"Failed to sync config to LiteLLM: {e}")

    async def get_default_config(self) -> Optional[LLMConfig]:
        """获取默认配置"""
        return await llm_config_repository.get_default_config()

    async def test_config(self, config_id: int) -> Dict[str, Any]:
        """
        测试配置连通性

        Args:
            config_id: 配置ID

        Returns:
            Dict: 测试结果
        """
        config = await self.get_by_id(config_id)
        api_key = config.api_key
        api_base = config.api_base
        model = config.model

        if not model or not api_key:
            raise HTTPException(status_code=400, detail="模型配置缺少 model_id 或 api_key")

        try:
            start_time = time.time()

            litellm_config = settings.LITELLM_CONFIG
            base_url = litellm_config.get("base_url", "http://localhost:4000")
            master_key = litellm_config.get("master_key", "")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {master_key}"
            }

            url = f"{base_url}/chat/completions"
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "Hello, this is a test message. Please respond with 'OK'."}],
                "max_tokens": 10
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=60)
                response.raise_for_status()
                result = response.json()

            latency_ms = int((time.time() - start_time) * 1000)
            model_response = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            return {
                "status": "success",
                "latency_ms": latency_ms,
                "model_response": model_response
            }

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="测试请求超时")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"测试请求失败: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")

    async def sync_to_gateway(self, config_id: Optional[int] = None) -> Dict[str, Any]:
        """
        同步配置到 LiteLLM 网关

        Args:
            config_id: 配置ID，为None时同步所有活跃配置

        Returns:
            Dict: 同步结果
        """
        try:
            if config_id:
                config = await self.get_by_id(config_id)
                success = await litellm_sync_service.add_or_update_config(config)
                return {
                    "success": success,
                    "message": f"配置 '{config.model_id}' {'同步成功' if success else '同步失败'}"
                }
            else:
                success = await litellm_sync_service.sync_all_configs()
                return {
                    "success": success,
                    "message": "所有活跃配置已同步到 LiteLLM 网关" if success else "同步过程中出现错误"
                }
        except Exception as e:
            logger.error(f"Failed to sync to gateway: {e}")
            return {
                "success": False,
                "message": f"同步失败: {str(e)}"
            }

    async def sync_from_gateway(self) -> Dict[str, Any]:
        """
        从 LiteLLM 网关同步模型配置到本地

        Returns:
            Dict: 同步结果统计
        """
        try:
            result = await litellm_sync_service.sync_from_gateway()
            return result
        except Exception as e:
            logger.error(f"Failed to sync from gateway: {e}")
            return {
                "total": 0,
                "created": 0,
                "updated": 0,
                "skipped": 0,
                "failed": 1,
                "errors": [f"同步失败: {str(e)}"]
            }

    async def get_gateway_models(self) -> List[Dict[str, Any]]:
        """
        获取 LiteLLM 网关中的模型列表

        Returns:
            List[Dict]: 网关中的模型列表
        """
        try:
            models = await litellm_sync_service.get_models_from_gateway()
            return models
        except Exception as e:
            logger.error(f"Failed to get gateway models: {e}")
            raise HTTPException(status_code=500, detail=f"获取网关模型失败: {str(e)}")


# 全局服务实例
llm_config_service = LLMConfigService()
