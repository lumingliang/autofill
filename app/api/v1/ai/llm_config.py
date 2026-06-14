"""
LLM 配置管理接口 (JWT 认证)

接收 HTTP 请求，调用 Service 层处理业务逻辑

约束：
- 只负责接收请求、参数校验、调用 Service 层
- 禁止直接操作数据库、直接访问 Repository 层
- 禁止直接查询 Model 层
- 认证已在中间件处理，API层不再重复认证
"""
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Query
from tortoise.expressions import Q

from app.core.ctx import Ctx
from app.core.dependency import is_superuser
from app.log import logger
from app.repositories.llm.llm_provider_repository import llm_provider_repository
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.llm_config import (
    LLMConfigCreate,
    LLMConfigTestRequest,
    LLMConfigUpdate,
)
from app.services.llm.llm_config_service import llm_config_service
from app.settings.config import settings

llm_config_router = APIRouter()


async def get_llm_providers_from_db() -> List[Dict[str, Any]]:
    """从数据库获取启用的模型提供商列表"""
    providers = await llm_provider_repository.get_active_providers()
    return [await p.to_dict() for p in providers]


@llm_config_router.get("/llm_config/list", summary="获取 LLM 配置列表")
async def list_llm_config(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    name: str = Query("", description="配置名称模糊查询"),
    model_provider: str = Query("", description="模型提供商筛选"),
    is_active: bool = Query(True, description="是否启用筛选"),
):
    """获取 LLM 配置列表"""
    # 构建查询条件
    q = Q()
    if name:
        q &= Q(name__contains=name)
    if model_provider:
        q &= Q(model_provider=model_provider)

    # 调用 Service 层
    total, configs = await llm_config_service.list_configs(
        page=page, page_size=page_size, search=q, order=["-updated_at"]
    )

    data = [await config.to_dict() for config in configs]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@llm_config_router.get("/llm_config/get", summary="获取 LLM 配置详情")
async def get_llm_config(
    id: int = Query(..., description="配置ID"),
):
    """获取 LLM 配置详情"""
    config = await llm_config_service.get_by_id(id)
    return Success(data=await config.to_dict())


@llm_config_router.post("/llm_config/create", summary="创建 LLM 配置")
async def create_llm_config(
    config_in: LLMConfigCreate,
):
    """创建 LLM 配置"""
    config = await llm_config_service.create_config(
        name=config_in.name,
        model_provider=config_in.model_provider,
        model=config_in.model,
        api_key=config_in.api_key,
        api_base=config_in.api_base,
        timeout=config_in.timeout,
        is_default=config_in.is_default,
        is_active=config_in.is_active,
        description=config_in.description
    )
    return Success(data=await config.to_dict())


@llm_config_router.post("/llm_config/update", summary="更新 LLM 配置")
async def update_llm_config(
    config_in: LLMConfigUpdate,
):
    """更新 LLM 配置"""
    updated = await llm_config_service.update_config(
        id=config_in.id,
        name=config_in.name,
        model_provider=config_in.model_provider,
        model=config_in.model,
        api_key=config_in.api_key,
        api_base=config_in.api_base,
        timeout=config_in.timeout,
        is_default=config_in.is_default,
        is_active=config_in.is_active,
        description=config_in.description
    )
    return Success(data=await updated.to_dict())


@llm_config_router.delete("/llm_config/delete", summary="删除 LLM 配置")
async def delete_llm_config(
    id: int = Query(..., description="配置ID"),
):
    """删除 LLM 配置"""
    await llm_config_service.delete_config(id=id)
    return Success(msg="删除成功")


@llm_config_router.get("/llm_config/providers", summary="获取模型提供商列表")
async def get_llm_providers():
    """获取模型提供商列表"""
    providers = await get_llm_providers_from_db()
    return Success(data=providers)


@llm_config_router.post("/llm_config/test", summary="测试配置连通性")
async def test_llm_config(
    request: LLMConfigTestRequest,
):
    """测试配置连通性"""
    result = await llm_config_service.test_config(request.id)
    return Success(data=result)


@llm_config_router.get("/llm_config/gateway/status", summary="获取 LiteLLM 网关状态")
async def get_gateway_status():
    """获取 LiteLLM 网关状态"""
    try:
        litellm_config = settings.LITELLM_CONFIG
        base_url = litellm_config.get("base_url", "http://localhost:4000")
        master_key = litellm_config.get("master_key", "")

        headers = {
            "Authorization": f"Bearer {master_key}"
        }

        async with httpx.AsyncClient() as client:
            # 获取健康状态
            health_response = await client.get(
                f"{base_url}/health",
                headers=headers,
                timeout=10
            )

            # 获取模型列表
            models_response = await client.get(
                f"{base_url}/model/info",
                headers=headers,
                timeout=10
            )

        return Success(data={
            "status": "healthy" if health_response.status_code == 200 else "unhealthy",
            "version": "1.66.1",  # LiteLLM 版本
            "models_loaded": len(models_response.json().get("data", [])) if models_response.status_code == 200 else 0,
            "gateway_url": base_url
        })

    except Exception as e:
        logger.error(f"Failed to get gateway status: {e}")
        return Success(data={
            "status": "unhealthy",
            "error": str(e),
            "gateway_url": settings.LITELLM_CONFIG.get("base_url", "http://localhost:4000")
        })


@llm_config_router.post("/llm_config/sync_to_gateway", summary="同步配置到 LiteLLM 网关")
async def sync_to_gateway(
    id: Optional[int] = Query(None, description="配置ID，不传则同步所有活跃配置"),
):
    """同步配置到 LiteLLM 网关"""
    current_user = Ctx.get_user()

    # 权限检查 - 只允许超级管理员
    if not is_superuser(current_user):
        return Fail(code=403, msg="无权执行此操作")

    result = await llm_config_service.sync_to_gateway(config_id=id)
    if result["success"]:
        return Success(data=result, msg=result["message"])
    else:
        return Fail(code=500, msg=result["message"])


@llm_config_router.post("/llm_config/sync_from_gateway", summary="从 LiteLLM 网关同步配置")
async def sync_from_gateway():
    """从 LiteLLM 网关同步模型配置到本地数据库"""
    current_user = Ctx.get_user()

    # 权限检查 - 只允许超级管理员
    if not is_superuser(current_user):
        return Fail(code=403, msg="无权执行此操作")

    result = await llm_config_service.sync_from_gateway()
    return Success(data=result, msg=f"同步完成: 总计 {result['total']}, 新建 {result['created']}, 更新 {result['updated']}, 跳过 {result['skipped']}, 失败 {result['failed']}")


@llm_config_router.get("/llm_config/gateway/models", summary="获取 LiteLLM 网关模型列表")
async def get_gateway_models():
    """获取 LiteLLM 网关中的模型列表"""
    current_user = Ctx.get_user()

    # 权限检查 - 只允许超级管理员
    if not is_superuser(current_user):
        return Fail(code=403, msg="无权执行此操作")

    models = await llm_config_service.get_gateway_models()
    return Success(data=models)
