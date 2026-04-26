"""
智能填单系统公开接口 (Dify/三方应用调用)
使用 API Key 认证，不依赖 JWT
"""
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, Header, Request
from fastapi.exceptions import HTTPException
from tortoise.expressions import Q

from app.controllers.autofill import (dropdown_option_controller,
                                      fill_data_record_controller,
                                      summary_template_controller)
from app.core.autofill_auth import APIKeyAuth
from app.core.request_parser import parse_request_params
from app.schemas.base import Fail, Success
from app.schemas.autofill import *
from app.settings.config import settings

logger = logging.getLogger(__name__)

autofill_public_router = APIRouter()


# ==================== Dify 调用接口 ====================

async def list_summary_templates_handler(
    request: Request,
    auth_info: dict
):
    """
    查询模板列表处理逻辑
    """
    # 使用通用参数解析组件获取参数
    params = await parse_request_params(request, SummaryTemplateListRequest)
    
    q = Q(tenant_id=auth_info["tenant_id"], app_name=auth_info["app_name"])
    if params.get("class_name"):
        q &= Q(class_name=params["class_name"])

    templates = await summary_template_controller.model.filter(q).all()
    return Success(data=[
        {"id": t.id, "name": t.name, "summary": t.summary, "class_name": t.class_name}
        for t in templates
    ])


@autofill_public_router.get("/autofill/summary_template/list", summary="查询模板列表")
@autofill_public_router.post("/autofill/summary_template/list", summary="查询模板列表")
async def list_summary_templates(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    Dify调用: 根据 tenant_id + app_name + class_name 查询模板列表
    支持 GET 和 POST 方法
    支持参数传递方式: Query / Form-Data / JSON Body
    """
    return await list_summary_templates_handler(request, auth_info)


async def get_summary_template_handler(
    request: Request,
    auth_info: dict
):
    """
    查询模板详情处理逻辑
    """
    # 使用通用参数解析组件获取参数
    params = await parse_request_params(request, SummaryTemplateDetailRequest)
    
    template = await summary_template_controller.model.filter(
        id=params["id"],
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"]
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return Success(data={
        "id": template.id,
        "name": template.name,
        "summary": template.summary,
        "class_name": template.class_name,
        "template_content": template.template_content
    })


@autofill_public_router.get("/autofill/summary_template", summary="查询模板详情")
@autofill_public_router.post("/autofill/summary_template", summary="查询模板详情")
async def get_summary_template(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    Dify调用: 根据ID查询模板详情
    支持 GET 和 POST 方法
    支持参数传递方式: Query / Form-Data / JSON Body
    """
    return await get_summary_template_handler(request, auth_info)


async def list_dropdown_options_handler(
    request: Request,
    auth_info: dict
):
    """
    查询下拉选项列表处理逻辑
    """
    # 使用通用参数解析组件获取参数
    params = await parse_request_params(request, DropdownOptionListRequest)
    
    q = Q(tenant_id=auth_info["tenant_id"], app_name=auth_info["app_name"])
    if params.get("class_name"):
        q &= Q(class_name=params["class_name"])

    # parent_id 默认为0，表示查询顶级选项
    parent_id = params.get("parent_id", 0)
    q &= Q(parent_id=parent_id)

    options = await dropdown_option_controller.model.filter(q).all()
    return Success(data=[
        {
            "id": o.id,
            "option_value": o.option_value,
            "summary": o.summary,
            "has_children": await dropdown_option_controller.model.filter(parent_id=o.id).exists()
        }
        for o in options
    ])


@autofill_public_router.get("/autofill/dropdown_options/list", summary="查询下拉选项列表")
@autofill_public_router.post("/autofill/dropdown_options/list", summary="查询下拉选项列表")
async def list_dropdown_options(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    Dify调用: 根据 app_name + class_name + parent_id 查询下拉选项列表
    支持 GET 和 POST 方法
    支持参数传递方式: Query / Form-Data / JSON Body
    """
    return await list_dropdown_options_handler(request, auth_info)


async def get_dropdown_option_handler(
    request: Request,
    auth_info: dict
):
    """
    查询下拉选项详情处理逻辑
    """
    # 使用通用参数解析组件获取参数
    params = await parse_request_params(request, DropdownOptionDetailRequest)
    
    # 根据ID查询选项
    option = await dropdown_option_controller.model.filter(
        id=params["id"],
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"]
    ).first()

    if not option:
        raise HTTPException(status_code=404, detail="Option not found")

    # 查询子选项
    children = await dropdown_option_controller.model.filter(
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"],
        parent_id=option.id
    ).all()

    return Success(data={
        "id": option.id,
        "option_value": option.option_value,
        "summary": option.summary,
        "description": option.description,
        "class_name": option.class_name,
        "children": [
            {"id": c.id, "option_value": c.option_value, "summary": c.summary}
            for c in children
        ]
    })


@autofill_public_router.get("/autofill/dropdown_options", summary="查询下拉选项详情")
@autofill_public_router.post("/autofill/dropdown_options", summary="查询下拉选项详情")
async def get_dropdown_option(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    Dify调用: 根据ID查询选项详情及其子选项
    支持 GET 和 POST 方法
    支持参数传递方式: Query / Form-Data / JSON Body
    """
    return await get_dropdown_option_handler(request, auth_info)


async def record_fill_data_handler(
    request: Request,
    auth_info: dict
):
    """
    记录填单数据处理逻辑
    """
    # 使用通用参数解析组件获取参数
    params = await parse_request_params(request, RecordFillDataRequest)
    
    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    record = await fill_data_record_controller.record_fill_data(
        session_id=params["session_id"],
        tenant_id=tenant_id,
        app_name=app_name,
        data=params.get("data", {}),
        phone=params.get("phone"),
        user_unique_id=params.get("user_unique_id"),
        user_name=params.get("user_name")
    )

    return Success(msg="success", data={"id": record.id})


@autofill_public_router.get("/autofill/record_fill_data", summary="记录填单数据")
@autofill_public_router.post("/autofill/record_fill_data", summary="记录填单数据")
async def record_fill_data(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    Dify调用: 记录填单数据，支持数据合并
    支持 GET 和 POST 方法
    支持参数传递方式: Query / Form-Data / JSON Body
    """
    return await record_fill_data_handler(request, auth_info)


async def get_ai_fill_data_handler(
    request: Request,
    auth_info: dict
):
    """
    获取AI填单数据处理逻辑
    """
    # 使用通用参数解析组件获取参数
    params = await parse_request_params(request, AIFillDataRequest)
    
    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 1. 存储原始数据到数据库
    await fill_data_record_controller.save_original_data(
        session_id=params["session_id"],
        tenant_id=tenant_id,
        app_name=app_name,
        data=params["data"]
    )

    # 2. 转发请求到 Dify
    dify_url = auth_info["dify_url"]
    dify_api_key = auth_info["dify_api_key"]
    dify_timeout = settings.DIFY_TIMEOUT

    if not dify_url or not dify_api_key:
        raise HTTPException(status_code=500, detail="Dify configuration not found")

    # 构建转发请求
    headers = {
        "Authorization": f"Bearer {dify_api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": {
            "data": params["data"],
        },
        "response_mode": "blocking",
        "conversation_id": "",
        "user": params["session_id"]
    }

    try:
        async with httpx.AsyncClient(timeout=dify_timeout) as client:
            response = await client.post(
                dify_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return Success(data=response.json())
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Dify service timeout")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Dify service error: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@autofill_public_router.get("/autofill/get_ai_fill_data", summary="获取AI填单数据")
@autofill_public_router.post("/autofill/get_ai_fill_data", summary="获取AI填单数据")
async def get_ai_fill_data(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    三方应用调用: 接收请求 -> 存储数据 -> 转发Dify -> 返回响应
    支持 GET 和 POST 方法
    支持参数传递方式: Query / Form-Data / JSON Body
    """
    return await get_ai_fill_data_handler(request, auth_info)
