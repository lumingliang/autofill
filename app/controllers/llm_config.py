"""
LLM 配置管理 Controller
"""
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi.exceptions import HTTPException
from tortoise.expressions import Q

from app.core.crud import CRUDBase
from app.models.llm_config import LLMConfig
from app.schemas.llm_config import LLMConfigCreate, LLMConfigUpdate
from app.settings.config import settings


class LLMConfigController(CRUDBase[LLMConfig, LLMConfigCreate, LLMConfigUpdate]):
    def __init__(self):
        super().__init__(model=LLMConfig)

    async def create_config(self, obj_in: LLMConfigCreate) -> LLMConfig:
        """创建 LLM 配置"""
        # 检查同一租户下配置名称是否已存在
        tenant_id = obj_in.tenant_id or 0
        existing = await self.model.filter(
            tenant_id=tenant_id,
            name=obj_in.name
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="该租户下已存在同名配置")

        # 准备数据
        data = obj_in.model_dump()
        data["capabilities"] = LLMConfig.get_default_capabilities()

        # 如果设置为默认配置，取消其他默认配置
        if data.get("is_default"):
            await self.model.filter(tenant_id=tenant_id).update(is_default=False)

        # 创建配置
        config = await self.create(data)

        # 同步到 LiteLLM 网关
        await self._sync_to_litellm(config, action="create")

        return config

    def _is_masked_api_key(self, api_key: str) -> bool:
        """检查 api_key 是否为脱敏格式"""
        if not api_key:
            return False
        # 脱敏格式示例: ms-9****f738, sk-abc****xyz, ••••••••••••
        return '****' in api_key or '••••' in api_key or api_key.count('•') > 3

    async def update_config(self, id: int, obj_in: LLMConfigUpdate) -> LLMConfig:
        """更新 LLM 配置"""
        config = await self.get(id=id)

        # 如果修改了名称，检查唯一性
        if obj_in.name and obj_in.name != config.name:
            tenant_id = obj_in.tenant_id or config.tenant_id or 0
            existing = await self.model.filter(
                tenant_id=tenant_id,
                name=obj_in.name
            ).exclude(id=id).first()
            if existing:
                raise HTTPException(status_code=400, detail="该租户下已存在同名配置")

        # 如果设置为默认配置，取消其他默认配置
        if obj_in.is_default:
            tenant_id = obj_in.tenant_id or config.tenant_id or 0
            await self.model.filter(tenant_id=tenant_id).exclude(id=id).update(is_default=False)

        # 准备更新数据
        update_data = obj_in.model_dump(exclude_unset=True, exclude={"id"})

        # 检查 litellm_params 中的 api_key 是否被脱敏
        litellm_params = update_data.get("litellm_params", {})
        if litellm_params and "api_key" in litellm_params:
            new_api_key = litellm_params["api_key"]
            if self._is_masked_api_key(new_api_key):
                # 如果 api_key 被脱敏，保留原来的值
                old_litellm_params = config.litellm_params or {}
                litellm_params["api_key"] = old_litellm_params.get("api_key", "")
                update_data["litellm_params"] = litellm_params

        # 更新配置
        updated = await self.update(id=id, obj_in=update_data)

        # 同步到 LiteLLM 网关
        await self._sync_to_litellm(updated, action="update")

        return updated

    async def delete_config(self, id: int) -> None:
        """删除 LLM 配置"""
        config = await self.get(id=id)

        # 从 LiteLLM 网关移除
        await self._sync_to_litellm(config, action="delete")

        # 删除配置
        await config.delete()

    async def get_default_config(self, tenant_id: int = 0, app_name: str = None) -> Optional[LLMConfig]:
        """获取默认配置"""
        q = Q(tenant_id=tenant_id, is_active=True)
        if app_name:
            q &= Q(app_name=app_name)

        # 优先获取租户+应用的默认配置
        config = await self.model.filter(q, is_default=True).first()
        if config:
            return config

        # 其次获取租户级别的默认配置
        config = await self.model.filter(tenant_id=tenant_id, is_default=True, is_active=True).first()
        if config:
            return config

        # 最后获取系统级别的默认配置 (tenant_id=0)
        config = await self.model.filter(tenant_id=0, is_default=True, is_active=True).first()
        if config:
            return config

        # 如果没有默认配置，返回第一个活跃配置
        return await self.model.filter(tenant_id=tenant_id, is_active=True).first()

    async def list_configs(
        self,
        page: int,
        page_size: int,
        search: Q = Q(),
        order: list = None
    ) -> Tuple[int, List[LLMConfig]]:
        """获取配置列表"""
        if order is None:
            order = ["-updated_at"]
        query = self.model.filter(search)
        return await query.count(), await query.offset((page - 1) * page_size).limit(page_size).order_by(*order)

    async def reset_method_status(self, id: int, methods: Optional[List[str]] = None) -> LLMConfig:
        """重置模型方法状态"""
        config = await self.get(id=id)
        capabilities = config.capabilities or LLMConfig.get_default_capabilities()
        structured_methods = capabilities.get("structured_output_methods", {})

        if methods:
            # 重置指定方法
            for method in methods:
                if method in structured_methods:
                    structured_methods[method] = {
                        "supported": True,
                        "failed_count": 0,
                        "last_error": None,
                        "last_attempt": None
                    }
        else:
            # 重置所有方法
            capabilities = LLMConfig.get_default_capabilities()

        config.capabilities = capabilities
        await config.save()
        return config

    async def update_method_status(
        self,
        id: int,
        method: str,
        supported: bool,
        failed_count: int = 0,
        last_error: str = None
    ) -> LLMConfig:
        """更新方法状态"""
        config = await self.get(id=id)
        capabilities = config.capabilities or LLMConfig.get_default_capabilities()
        structured_methods = capabilities.get("structured_output_methods", {})

        if method in structured_methods:
            from datetime import datetime
            structured_methods[method]["supported"] = supported
            structured_methods[method]["failed_count"] = failed_count
            structured_methods[method]["last_error"] = last_error
            structured_methods[method]["last_attempt"] = datetime.now().isoformat()

        config.capabilities = capabilities
        await config.save()
        return config

    async def _sync_to_litellm(self, config: LLMConfig, action: str = "create"):
        """同步配置到 LiteLLM 网关"""
        # 延迟导入避免循环导入
        from app.services.llm.litellm_sync_service import litellm_sync_service

        try:
            if action in ["create", "update"]:
                # 添加或更新配置
                await litellm_sync_service.add_or_update_config(config)
            elif action == "delete":
                # 删除配置
                await litellm_sync_service.remove_config(config.name)

        except Exception as e:
            # 记录错误但不影响主流程
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to sync config to LiteLLM: {e}")

    async def test_config(self, config: LLMConfig) -> Dict[str, Any]:
        """测试配置连通性"""
        import time
        from datetime import datetime

        litellm_params = config.litellm_params or {}
        api_key = litellm_params.get("api_key", "")
        api_base = litellm_params.get("api_base", None)

        # 使用配置名称作为模型名称（对应 LiteLLM 网关的 model_list 中的 model_name）
        model = config.name

        if not model or not api_key:
            raise HTTPException(status_code=400, detail="模型配置缺少 model 或 api_key")

        try:
            start_time = time.time()

            # 使用 LiteLLM 或直接调用测试
            litellm_config = settings.LITELLM_CONFIG
            base_url = litellm_config.get("base_url", "http://localhost:4000")
            master_key = litellm_config.get("master_key", "")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {master_key}"
            }

            # 通过 LiteLLM 网关测试
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


# 全局控制器实例
llm_config_controller = LLMConfigController()
