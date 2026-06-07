#!/usr/bin/env python3
"""
权限缓存服务 - 统一管理用户权限缓存
"""
from typing import Set, Optional
from app.core.redis import redis_client
from app.log import logger
from app.repositories import api_repository, user_role_repository, role_api_repository, role_repository


class PermissionCacheService:
    """权限缓存服务"""

    @staticmethod
    def _get_cache_key(user_id: int, tenant_id: int) -> str:
        """生成缓存key"""
        return f"user_perms:{user_id}:{tenant_id}"

    @classmethod
    async def get_user_permissions(cls, user_id: int, tenant_id: int) -> Optional[Set[str]]:
        """
        获取用户权限 - 先查缓存，缓存未命中则查数据库
        
        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            
        Returns:
            用户拥有的api_code集合，如果无权限返回None
        """
        cache_key = cls._get_cache_key(user_id, tenant_id)

        # 1. 尝试从缓存获取
        cached_perms = await redis_client.get_json(cache_key)
        if cached_perms is not None:
            logger.debug(f"用户 {user_id} 在租户 {tenant_id} 的权限从缓存获取，共 {len(cached_perms)} 个")
            return set(cached_perms)

        # 2. 缓存未命中，从数据库获取
        perms = await cls._load_permissions_from_db(user_id, tenant_id)

        # 3. 写入缓存
        if perms is not None:
            await redis_client.set_json(cache_key, list(perms), ttl=300)
            logger.debug(f"用户 {user_id} 在租户 {tenant_id} 的权限已缓存，共 {len(perms)} 个")

        return perms

    @classmethod
    async def _load_permissions_from_db(cls, user_id: int, tenant_id: int) -> Optional[Set[str]]:
        """从数据库加载用户权限（使用 repository，自动租户过滤）"""
        # 使用 user_role_repository 获取用户角色
        role_ids = await user_role_repository.get_role_ids_by_user_id(user_id)
        if not role_ids or not tenant_id:
            return None

        # 使用 role_api_repository 获取角色绑定的API
        api_ids_mapping = await role_api_repository.batch_get_api_ids_by_role_ids(role_ids)
        all_api_ids = list({aid for ids in api_ids_mapping.values() for aid in ids})

        if not all_api_ids:
            return set()

        # 使用 api_repository 查询API codes
        api_codes = await api_repository.get_codes_by_ids(all_api_ids)
        return set(api_codes)

    @classmethod
    async def clear_user_cache(cls, user_id: int, tenant_id: int) -> None:
        """
        清除指定用户在指定租户下的权限缓存
        
        Args:
            user_id: 用户ID
            tenant_id: 租户ID
        """
        cache_key = cls._get_cache_key(user_id, tenant_id)
        await redis_client.delete(cache_key)
        logger.info(f"用户 {user_id} 在租户 {tenant_id} 的权限缓存已清除")

    @classmethod
    async def clear_role_users_cache(cls, role_id: int) -> int:
        """
        清除拥有指定角色的所有用户的权限缓存

        注意：角色属于特定租户，只清除该租户下的用户缓存

        Args:
            role_id: 角色ID

        Returns:
            清除的缓存数量
        """
        # 获取角色信息，确认所属租户
        role = await role_repository.get_by_id(role_id)
        if not role:
            return 0

        # 使用 user_role_repository 获取该角色下的所有用户
        user_ids = await user_role_repository.get_user_ids_by_role_id(role_id)
        if not user_ids:
            return 0

        # 只清除该角色所属租户下的缓存
        tenant_id = role.tenant_id
        deleted_count = 0
        for user_id in user_ids:
            cache_key = cls._get_cache_key(user_id, tenant_id)
            await redis_client.delete(cache_key)
            deleted_count += 1

        logger.info(f"角色 {role_id} 的权限已变更，清除了 {len(user_ids)} 个用户的权限缓存，共 {deleted_count} 条")
        return deleted_count


# 导出单例
permission_cache_service = PermissionCacheService()
