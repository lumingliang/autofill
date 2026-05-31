"""
LLM 配置管理接口 (JWT 认证)
"""
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Header, Query
from tortoise.expressions import Q

from app.controllers.llm_config import llm_config_controller
from app.core.dependency import AuthControl, is_superuser
from app.log import logger
from app.repositories.llm.llm_provider_repository import llm_provider_repository
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.llm_config import (
    LLMConfigCreate,
    LLMConfigListRequest,
    LLMConfigResetMethodsRequest,
    LLMConfigTestRequest,
    LLMConfigUpdate,
)
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
    token: str = Header(..., description="token验证"),
):
    """获取 LLM 配置列表"""
    await AuthControl.is_authed(token)

    # 构建查询条件
    q = Q()
    if name:
        q &= Q(name__contains=name)
    if model_provider:
        q &= Q(model_provider=model_provider)
    # is_active 默认True，不需要额外判断

    total, configs = await llm_config_controller.list_configs(
        page=page, page_size=page_size, search=q, order=["-updated_at"]
    )

    data = [await config.to_dict() for config in configs]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@llm_config_router.get("/llm_config/get", summary="获取 LLM 配置详情")
async def get_llm_config(
    id: int = Query(..., description="配置ID"),
    token: str = Header(..., description="token验证"),
):
    """获取 LLM 配置详情"""
    await AuthControl.is_authed(token)
    config = await llm_config_controller.get(id=id)
    return Success(data=await config.to_dict())


@llm_config_router.post("/llm_config/create", summary="创建 LLM 配置")
async def create_llm_config(
    config_in: LLMConfigCreate,
    token: str = Header(..., description="token验证"),
):
    """创建 LLM 配置"""
    await AuthControl.is_authed(token)

    config = await llm_config_controller.create_config(config_in)
    return Success(data=await config.to_dict())


@llm_config_router.post("/llm_config/update", summary="更新 LLM 配置")
async def update_llm_config(
    config_in: LLMConfigUpdate,
    token: str = Header(..., description="token验证"),
):
    """更新 LLM 配置"""
    await AuthControl.is_authed(token)

    updated = await llm_config_controller.update_config(id=config_in.id, obj_in=config_in)
    return Success(data=await updated.to_dict())


@llm_config_router.delete("/llm_config/delete", summary="删除 LLM 配置")
async def delete_llm_config(
    id: int = Query(..., description="配置ID"),
    token: str = Header(..., description="token验证"),
):
    """删除 LLM 配置"""
    await AuthControl.is_authed(token)

    await llm_config_controller.delete_config(id=id)
    return Success(msg="删除成功")


@llm_config_router.get("/llm_config/providers", summary="获取模型提供商列表")
async def get_llm_providers(
    token: str = Header(..., description="token验证"),
):
    """获取模型提供商列表"""
    await AuthControl.is_authed(token)
    providers = await get_llm_providers_from_db()
    return Success(data=providers)


@llm_config_router.post("/llm_config/test", summary="测试配置连通性")
async def test_llm_config(
    request: LLMConfigTestRequest,
    token: str = Header(..., description="token验证"),
):
    """测试配置连通性"""
    await AuthControl.is_authed(token)
    config = await llm_config_controller.get(id=request.id)

    result = await llm_config_controller.test_config(config)
    return Success(data=result)


@llm_config_router.get("/llm_config/gateway/status", summary="获取 LiteLLM 网关状态")
async def get_gateway_status(
    token: str = Header(..., description="token验证"),
):
    """获取 LiteLLM 网关状态"""
    await AuthControl.is_authed(token)

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


@llm_config_router.post("/llm_config/reset_methods", summary="重置模型方法状态")
async def reset_llm_methods(
    request: LLMConfigResetMethodsRequest,
    token: str = Header(..., description="token验证"),
):
    """重置模型方法状态"""
    await AuthControl.is_authed(token)

    updated = await llm_config_controller.reset_method_status(
        id=request.id,
        methods=request.methods
    )
    return Success(data=await updated.to_dict())


@llm_config_router.get("/llm_config/methods", summary="获取模型方法状态")
async def get_llm_methods(
    id: int = Query(..., description="配置ID"),
    token: str = Header(..., description="token验证"),
):
    """获取模型方法状态"""
    await AuthControl.is_authed(token)
    config = await llm_config_controller.get(id=id)

    return Success(data={
        "model_id": config.id,
        "model_name": config.name,
        "capabilities": config.capabilities
    })


@llm_config_router.post("/llm_config/sync_to_gateway", summary="同步配置到 LiteLLM 网关")
async def sync_to_gateway(
    id: Optional[int] = Query(None, description="配置ID，不传则同步所有活跃配置"),
    token: str = Header(..., description="token验证"),
):
    """同步配置到 LiteLLM 网关"""
    current_user = await AuthControl.is_authed(token)

    # 权限检查 - 只允许超级管理员
    if not is_superuser(current_user):
        return Fail(code=403, msg="无权执行此操作")

    result = await llm_config_controller.sync_to_gateway(config_id=id)
    if result["success"]:
        return Success(data=result, msg=result["message"])
    else:
        return Fail(code=500, msg=result["message"])


@llm_config_router.post("/llm_config/sync_from_gateway", summary="从 LiteLLM 网关同步配置")
async def sync_from_gateway(
    token: str = Header(..., description="token验证"),
):
    """从 LiteLLM 网关同步模型配置到本地数据库"""
    current_user = await AuthControl.is_authed(token)

    # 权限检查 - 只允许超级管理员
    if not is_superuser(current_user):
        return Fail(code=403, msg="无权执行此操作")

    result = await llm_config_controller.sync_from_gateway()
    return Success(data=result, msg=f"同步完成: 总计 {result['total']}, 新建 {result['created']}, 更新 {result['updated']}, 跳过 {result['skipped']}, 失败 {result['failed']}")


@llm_config_router.get("/llm_config/gateway/models", summary="获取 LiteLLM 网关模型列表")
async def get_gateway_models(
    token: str = Header(..., description="token验证"),
):
    """获取 LiteLLM 网关中的模型列表"""
    current_user = await AuthControl.is_authed(token)

    # 权限检查 - 只允许超级管理员
    if not is_superuser(current_user):
        return Fail(code=403, msg="无权执行此操作")

    models = await llm_config_controller.get_gateway_models()
    return Success(data={
        "total": len(models),
        "models": models
    })
