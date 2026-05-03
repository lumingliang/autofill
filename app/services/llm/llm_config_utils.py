"""
LLM 配置工具函数
提供 Service 层获取 LLM 配置的公共函数
禁止依赖 Controller，直接操作 Model
"""
from typing import Optional

from tortoise.expressions import Q

from app.models.llm_config import LLMConfig


async def get_default_llm_config(tenant_id: int = 0, app_name: str = None) -> Optional[LLMConfig]:
    """
    获取默认 LLM 配置

    优先级：
    1. 租户+应用的默认配置
    2. 租户级别的默认配置
    3. 系统级别的默认配置 (tenant_id=0)
    4. 第一个活跃配置

    Args:
        tenant_id: 租户ID
        app_name: 应用名称

    Returns:
        LLMConfig 或 None
    """
    query = Q(tenant_id=tenant_id, is_active=True)
    if app_name:
        query &= Q(app_name=app_name)

    # 优先获取租户+应用的默认配置
    config = await LLMConfig.filter(query, is_default=True).first()
    if config:
        return config

    # 其次获取租户级别的默认配置
    config = await LLMConfig.filter(tenant_id=tenant_id, is_default=True, is_active=True).first()
    if config:
        return config

    # 最后获取系统级别的默认配置 (tenant_id=0)
    config = await LLMConfig.filter(tenant_id=0, is_default=True, is_active=True).first()
    if config:
        return config

    # 如果没有默认配置，返回第一个活跃配置
    return await LLMConfig.filter(tenant_id=tenant_id, is_active=True).first()
