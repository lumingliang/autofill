"""
LLM 配置控制器
"""
from typing import Optional

from tortoise.expressions import Q

from app.core.crud import CRUDBase
from app.core.redis import redis_client
from app.models.llm_config import LLMConfig
from app.schemas.llm_config import LLMConfigCreate, LLMConfigUpdate


class LLMConfigController(CRUDBase[LLMConfig, LLMConfigCreate, LLMConfigUpdate]):
    """LLM配置控制器"""

    def __init__(self):
        super().__init__(model=LLMConfig)

    async def get_list(
        self,
        page: int,
        page_size: int,
        tenant_id: Optional[int],
        is_superuser: bool,
        name: Optional[str] = None,
        model_provider: Optional[str] = None,
        is_active: Optional[bool] = None,
    ):
        """
        获取LLM配置列表
        - 超管：可以看到所有配置
        - 普通用户：只能看到全局配置(tenant_id为null)和自己的租户配置
        """
        q = Q()

        if name:
            q &= Q(name__contains=name)
        if model_provider:
            q &= Q(model_provider=model_provider)
        if is_active is not None:
            q &= Q(is_active=is_active)

        # 权限控制
        if is_superuser:
            # 超管可以看到所有配置，但如果指定了tenant_id，可以筛选
            if tenant_id is not None:
                q &= Q(tenant_id=tenant_id) | Q(tenant_id__isnull=True)
        else:
            # 普通用户：只能看到全局配置和自己的租户配置
            if tenant_id is not None:
                q &= Q(tenant_id=tenant_id) | Q(tenant_id__isnull=True)
            else:
                # 未指定租户时，只能看到全局配置
                q &= Q(tenant_id__isnull=True)

        total, configs = await self.list(
            page=page, page_size=page_size, search=q, order=["-is_default", "-updated_at"]
        )
        return total, configs

    async def get_by_id_with_permission(self, id: int, tenant_id: Optional[int], is_superuser: bool):
        """根据ID获取配置，并检查权限"""
        config = await self.get(id=id)

        if not config:
            return None

        # 权限检查
        if not is_superuser:
            # 普通用户只能访问全局配置或自己的租户配置
            if config.tenant_id is not None and config.tenant_id != tenant_id:
                return None

        return config

    async def create_config(self, obj_in: LLMConfigCreate, current_tenant_id: Optional[int], is_superuser: bool):
        """创建配置"""
        # 确定租户ID
        if is_superuser:
            # 超管可以创建全局配置或指定租户配置
            target_tenant_id = obj_in.tenant_id
        else:
            # 普通用户只能创建自己租户的配置
            target_tenant_id = current_tenant_id
            if not target_tenant_id:
                raise ValueError("您当前未选择租户，无法创建配置")

        # 如果设置为默认配置，需要取消其他默认配置
        if obj_in.is_default:
            await self._clear_default_config(target_tenant_id)

        # 创建配置
        config_data = obj_in.model_dump()
        config_data["tenant_id"] = target_tenant_id

        config = await self.create(obj_in=config_data)

        # 清除缓存
        await self._clear_cache(target_tenant_id)

        return config

    async def update_config(
        self, id: int, obj_in: LLMConfigUpdate, current_tenant_id: Optional[int], is_superuser: bool
    ):
        """更新配置"""
        config = await self.get(id=id)
        if not config:
            raise ValueError("配置不存在")

        # 权限检查
        if not is_superuser:
            if config.tenant_id is not None and config.tenant_id != current_tenant_id:
                raise ValueError("无权操作其他租户的配置")

        # 如果设置为默认配置，需要取消其他默认配置
        if obj_in.is_default and not config.is_default:
            await self._clear_default_config(config.tenant_id)

        # 更新配置
        updated = await self.update(id=id, obj_in=obj_in)

        # 清除缓存
        await self._clear_cache(config.tenant_id)

        return updated

    async def delete_config(self, id: int, current_tenant_id: Optional[int], is_superuser: bool):
        """删除配置"""
        config = await self.get(id=id)
        if not config:
            raise ValueError("配置不存在")

        # 权限检查
        if not is_superuser:
            if config.tenant_id is not None and config.tenant_id != current_tenant_id:
                raise ValueError("无权操作其他租户的配置")

        # 删除配置
        await self.remove(id=id)

        # 清除缓存
        await self._clear_cache(config.tenant_id)

        return True

    async def get_default_config(self, tenant_id: Optional[int] = None) -> Optional[LLMConfig]:
        """获取默认配置"""
        # 先尝试获取租户特定的默认配置
        if tenant_id is not None:
            config = await self.model.filter(tenant_id=tenant_id, is_default=True, is_active=True).first()
            if config:
                return config

        # 再尝试获取全局默认配置
        config = await self.model.filter(tenant_id__isnull=True, is_default=True, is_active=True).first()
        return config

    async def get_config_by_app_key(self, app_key: str) -> Optional[LLMConfig]:
        """
        根据app_key获取LLM配置
        使用Redis缓存
        """
        cache_key = redis_client.key(f"llm_config:app_key:{app_key}")

        # 尝试从缓存获取
        try:
            import json

            cached = await redis_client.client.get(cache_key)
            if cached:
                config_data = json.loads(cached)
                # 从缓存数据重建对象
                config = await self.get(config_data["id"])
                if config and config.is_active:
                    return config
        except Exception:
            pass

        # 从数据库查询
        # 先根据app_key找到应用，再找到对应的租户
        from app.models.autofill import AppManagement

        app = await AppManagement.filter(api_key=app_key, is_active=True).first()
        if not app:
            return None

        # 获取该租户的默认配置
        config = await self.get_default_config(app.tenant_id)

        # 写入缓存
        if config:
            try:
                config_dict = await config.to_dict()
                await redis_client.client.setex(cache_key, 3600, json.dumps(config_dict))  # 1小时缓存
            except Exception:
                pass

        return config

    async def _clear_default_config(self, tenant_id: Optional[int]):
        """清除默认配置标记"""
        if tenant_id is not None:
            await self.model.filter(tenant_id=tenant_id, is_default=True).update(is_default=False)
        else:
            await self.model.filter(tenant_id__isnull=True, is_default=True).update(is_default=False)

    async def _clear_cache(self, tenant_id: Optional[int]):
        """清除相关缓存"""
        try:
            # 清除该租户相关的缓存
            pattern = redis_client.key("llm_config:*")
            keys = await redis_client.client.keys(pattern)
            if keys:
                await redis_client.client.delete(*keys)
        except Exception:
            pass


llm_config_controller = LLMConfigController()
