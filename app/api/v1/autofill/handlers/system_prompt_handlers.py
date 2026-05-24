"""
系统提示词管理接口
提供系统提示词的CRUD操作
"""
from typing import Optional

from fastapi import APIRouter, Header, Query

from app.core.dependency import AuthControl
from app.core.tenant import TenantContext
from app.log import logger
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.system_prompt import (
    SystemPromptCreate,
    SystemPromptUpdate,
    SystemPromptListRequest
)
from app.services.autofill.system_prompt_service import system_prompt_service

router = APIRouter()


@router.get("/system_prompts", summary="系统提示词列表")
async def list_system_prompts(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    category: Optional[str] = Query(None, description="分类筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    is_default: Optional[bool] = Query(None, description="是否默认筛选"),
    is_active: Optional[bool] = Query(None, description="是否启用筛选"),
    tenant_id: int = Query(0, description="租户ID（超管用）"),
    token: str = Header(...),
):
    """
    获取系统提示词列表

    - 超管账号：可传入 tenant_id 筛选特定租户的提示词
    - 普通账号：不传 tenant_id，自动使用当前租户ID
    """
    current_user = await AuthControl.is_authed(token)

    # 判断是否为超管
    is_super = TenantContext.is_superuser()

    # 使用 TenantContext 获取有效的租户ID
    effective_tenant_id = TenantContext.get_tenant_id(tenant_id)

    try:
        result = await system_prompt_service.list_prompts(
            tenant_id=effective_tenant_id,
            category=category,
            keyword=keyword,
            is_default=is_default,
            is_active=is_active,
            page=page,
            page_size=page_size,
            is_superuser=is_super
        )
        return SuccessExtra(
            data=result["items"],
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"]
        )
    except Exception as e:
        logger.error(f"获取系统提示词列表失败: {e}")
        return Fail(code=500, msg=f"获取列表失败: {str(e)}")


@router.get("/system_prompts/categories", summary="获取所有分类")
async def get_categories(
    tenant_id: int = Query(0, description="租户ID（超管用）"),
    token: str = Header(...),
):
    """
    获取所有分类列表

    - 超管账号：可传入 tenant_id 筛选特定租户的分类
    - 普通账号：不传 tenant_id，自动使用当前租户ID
    """
    current_user = await AuthControl.is_authed(token)

    # 判断是否为超管
    is_super = TenantContext.is_superuser()

    # 使用 TenantContext 获取有效的租户ID
    effective_tenant_id = TenantContext.get_tenant_id(tenant_id)

    try:
        categories = await system_prompt_service.get_all_categories(
            tenant_id=effective_tenant_id,
            is_superuser=is_super
        )
        return Success(data=categories)
    except Exception as e:
        logger.error(f"获取分类列表失败: {e}")
        return Fail(code=500, msg=f"获取分类列表失败: {str(e)}")


@router.get("/system_prompts/{prompt_id}", summary="系统提示词详情")
async def get_system_prompt(
    prompt_id: int,
    tenant_id: int = Query(0, description="租户ID（超管用）"),
    token: str = Header(...),
):
    """获取系统提示词详情"""
    current_user = await AuthControl.is_authed(token)

    # 判断是否为超管
    is_super = TenantContext.is_superuser()

    # 使用 TenantContext 获取有效的租户ID
    effective_tenant_id = TenantContext.get_tenant_id(tenant_id)

    try:
        prompt = await system_prompt_service.get_prompt_by_id(
            prompt_id=prompt_id,
            tenant_id=effective_tenant_id,
            is_superuser=is_super
        )
        if not prompt:
            return Fail(code=404, msg="提示词不存在或无权访问")

        prompt_dict = await prompt.to_dict()
        return Success(data=prompt_dict)
    except Exception as e:
        logger.error(f"获取系统提示词详情失败: {e}")
        return Fail(code=500, msg=f"获取详情失败: {str(e)}")


@router.post("/system_prompts", summary="创建系统提示词")
async def create_system_prompt(
    prompt_in: SystemPromptCreate,
    tenant_id: int = Query(0, description="租户ID（超管用）"),
    token: str = Header(...),
):
    """
    创建系统提示词

    - 超管账号：可传入 tenant_id 指定租户
    - 普通账号：自动使用当前租户ID
    """
    current_user = await AuthControl.is_authed(token)

    # 使用 TenantContext 获取有效的租户ID
    effective_tenant_id = TenantContext.get_tenant_id(tenant_id)

    try:
        prompt = await system_prompt_service.create_prompt(
            name=prompt_in.name,
            content=prompt_in.content,
            tenant_id=effective_tenant_id,
            description=prompt_in.description,
            category=prompt_in.category,
            is_default=prompt_in.is_default,
            is_active=prompt_in.is_active
        )
        prompt_dict = await prompt.to_dict()
        return Success(data=prompt_dict)
    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except Exception as e:
        logger.error(f"创建系统提示词失败: {e}")
        return Fail(code=500, msg=f"创建失败: {str(e)}")


@router.post("/system_prompts/{prompt_id}", summary="更新系统提示词")
async def update_system_prompt(
    prompt_id: int,
    prompt_in: SystemPromptUpdate,
    tenant_id: int = Query(0, description="租户ID（超管用）"),
    token: str = Header(...),
):
    """
    更新系统提示词

    - 超管账号：可传入 tenant_id 指定租户
    - 普通账号：自动使用当前租户ID
    """
    current_user = await AuthControl.is_authed(token)

    # 使用 TenantContext 获取有效的租户ID
    effective_tenant_id = TenantContext.get_tenant_id(tenant_id)

    try:
        # 构建更新数据（排除None值）
        update_data = prompt_in.model_dump(exclude_unset=True, exclude_none=True)

        prompt = await system_prompt_service.update_prompt(
            prompt_id=prompt_id,
            tenant_id=effective_tenant_id,
            **update_data
        )
        prompt_dict = await prompt.to_dict()
        return Success(data=prompt_dict)
    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except Exception as e:
        logger.error(f"更新系统提示词失败: {e}")
        return Fail(code=500, msg=f"更新失败: {str(e)}")


@router.delete("/system_prompts/{prompt_id}", summary="删除系统提示词")
async def delete_system_prompt(
    prompt_id: int,
    tenant_id: int = Query(0, description="租户ID（超管用）"),
    token: str = Header(...),
):
    """
    删除系统提示词

    - 超管账号：可传入 tenant_id 指定租户，不传则删除任意租户（包括全局）的提示词
    - 普通账号：自动使用当前租户ID，不能删除全局提示词
    - 全局默认提示词（tenant_id=0）普通用户不允许删除
    """
    current_user = await AuthControl.is_authed(token)

    # 判断是否为超管
    is_super = TenantContext.is_superuser()

    # 使用 TenantContext 获取有效的租户ID
    effective_tenant_id = TenantContext.get_tenant_id(tenant_id)

    try:
        await system_prompt_service.delete_prompt(
            prompt_id=prompt_id,
            tenant_id=effective_tenant_id,
            is_superuser=is_super
        )
        return Success(msg="删除成功")
    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except Exception as e:
        logger.error(f"删除系统提示词失败: {e}")
        return Fail(code=500, msg=f"删除失败: {str(e)}")
