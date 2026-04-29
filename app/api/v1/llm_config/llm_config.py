"""
LLM 配置管理接口
"""
from typing import Optional

from fastapi import APIRouter, Header, Query
from tortoise.expressions import Q

from app.controllers.llm_config import llm_config_controller
from app.core.dependency import AuthControl
from app.models.admin import User
from app.schemas import Success, SuccessExtra, Fail
from app.schemas.llm_config import LLMConfigCreate, LLMConfigListRequest, LLMConfigUpdate
from app.models.llm_config import LLMProvider

router = APIRouter()


def is_superuser(user: User) -> bool:
    """检查是否为超级管理员"""
    return user.is_superuser


@router.get("/llm_config/list", summary="查看LLM配置列表")
async def list_llm_config(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    name: Optional[str] = Query(None, description="配置名称"),
    model_provider: Optional[str] = Query(None, description="模型提供商"),
    is_active: Optional[bool] = Query(None, description="是否启用"),
    token: str = Header(..., description="token验证"),
):
    """
    获取LLM配置列表
    - 超级管理员：返回所有配置
    - 普通用户：返回全局配置和自己的租户配置
    """
    current_user: User = await AuthControl.is_authed(token)

    total, configs = await llm_config_controller.get_list(
        page=page,
        page_size=page_size,
        tenant_id=current_user.current_tenant_id,
        is_superuser=is_superuser(current_user),
        name=name,
        model_provider=model_provider,
        is_active=is_active,
    )

    data = [await obj.to_dict() for obj in configs]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/llm_config/get", summary="查看LLM配置详情")
async def get_llm_config(
    id: int = Query(..., description="配置ID"),
    token: str = Header(..., description="token验证"),
):
    """获取LLM配置详情"""
    current_user: User = await AuthControl.is_authed(token)

    config = await llm_config_controller.get_by_id_with_permission(
        id=id,
        tenant_id=current_user.current_tenant_id,
        is_superuser=is_superuser(current_user),
    )

    if not config:
        return Fail(code=404, msg="配置不存在或无权限访问")

    data = await config.to_dict()
    return Success(data=data)


@router.post("/llm_config/create", summary="创建LLM配置")
async def create_llm_config(
    config_in: LLMConfigCreate,
    token: str = Header(..., description="token验证"),
):
    """创建LLM配置"""
    current_user: User = await AuthControl.is_authed(token)

    try:
        config = await llm_config_controller.create_config(
            obj_in=config_in,
            current_tenant_id=current_user.current_tenant_id,
            is_superuser=is_superuser(current_user),
        )
        return Success(data=await config.to_dict(), msg="创建成功")
    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except Exception as e:
        return Fail(code=500, msg=f"创建失败: {str(e)}")


@router.post("/llm_config/update", summary="更新LLM配置")
async def update_llm_config(
    config_in: LLMConfigUpdate,
    token: str = Header(..., description="token验证"),
):
    """更新LLM配置"""
    current_user: User = await AuthControl.is_authed(token)

    try:
        updated = await llm_config_controller.update_config(
            id=config_in.id,
            obj_in=config_in,
            current_tenant_id=current_user.current_tenant_id,
            is_superuser=is_superuser(current_user),
        )
        return Success(data=await updated.to_dict(), msg="更新成功")
    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except Exception as e:
        return Fail(code=500, msg=f"更新失败: {str(e)}")


@router.delete("/llm_config/delete", summary="删除LLM配置")
async def delete_llm_config(
    id: int = Query(..., description="配置ID"),
    token: str = Header(..., description="token验证"),
):
    """删除LLM配置"""
    current_user: User = await AuthControl.is_authed(token)

    try:
        await llm_config_controller.delete_config(
            id=id,
            current_tenant_id=current_user.current_tenant_id,
            is_superuser=is_superuser(current_user),
        )
        return Success(msg="删除成功")
    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except Exception as e:
        return Fail(code=500, msg=f"删除失败: {str(e)}")


@router.get("/llm_config/providers", summary="获取支持的模型提供商列表")
async def get_llm_providers(
    token: str = Header(..., description="token验证"),
):
    """获取支持的模型提供商列表"""
    await AuthControl.is_authed(token)

    providers = [
        {"value": provider[0], "label": provider[1]}
        for provider in LLMProvider.get_choices()
    ]
    return Success(data=providers)


@router.get("/llm_config/default", summary="获取默认配置")
async def get_default_config(
    token: str = Header(..., description="token验证"),
):
    """获取默认LLM配置"""
    current_user: User = await AuthControl.is_authed(token)

    config = await llm_config_controller.get_default_config(
        tenant_id=current_user.current_tenant_id
    )

    if not config:
        return Fail(code=404, msg="未找到默认配置")

    return Success(data=await config.to_dict())
