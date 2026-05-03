"""
智能填单系统公开接口 (Dify/三方应用调用)
使用 API Key 认证，不依赖 JWT
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, Request
from fastapi.exceptions import HTTPException
from tortoise.expressions import Q

from app.controllers.autofill import (dropdown_option_controller,
                                      field_group_config_controller,
                                      field_spec_controller,
                                      fill_data_record_controller,
                                      fill_page_controller,
                                      summary_template_controller)
from app.core.autofill_auth import APIKeyAuth
from app.core.request_parser import parse_request_params
from app.log import logger
from app.schemas.base import Fail, Success
from app.schemas.autofill import *
from app.services.ai_fill_service import get_ai_fill_service
from app.settings.config import settings

autofill_public_router = APIRouter()


# ==================== 模板相关接口 ====================

async def list_summary_templates_handler(
    request: Request,
    auth_info: dict
):
    """
    查询模板列表处理逻辑
    """
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


# ==================== 下拉选项接口 ====================

async def list_dropdown_options_handler(
    request: Request,
    auth_info: dict
):
    """
    查询下拉选项列表处理逻辑
    """
    params = await parse_request_params(request, DropdownOptionListRequest)
    
    q = Q(tenant_id=auth_info["tenant_id"], app_name=auth_info["app_name"])
    if params.get("class_name"):
        q &= Q(class_name=params["class_name"])

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
    params = await parse_request_params(request, DropdownOptionDetailRequest)
    
    option = await dropdown_option_controller.model.filter(
        id=params["id"],
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"]
    ).first()

    if not option:
        raise HTTPException(status_code=404, detail="Option not found")

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


# ==================== 填单数据接口 ====================

async def record_fill_data_handler(
    request: Request,
    auth_info: dict
):
    """
    记录填单数据处理逻辑
    """
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


# ==================== AI 填单接口 ====================

async def get_ai_fill_data_handler(
    request: Request,
    auth_info: dict
):
    """
    获取AI填单数据处理逻辑
    支持同步(sync)和异步(async)两种模式
    """
    params = await parse_request_params(request, AIFillDataRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]
    dify_url = auth_info["dify_url"]
    dify_api_key = auth_info["dify_api_key"]

    if not dify_url or not dify_api_key:
        raise HTTPException(status_code=500, detail="Dify configuration not found")

    service = get_ai_fill_service()
    response_mode = params.get("response_mode", "sync")

    if response_mode == "async":
        result = await service.process_async(
            session_id=params["session_id"],
            tenant_id=tenant_id,
            app_name=app_name,
            data=params["data"],
            dify_url=dify_url,
            dify_api_key=dify_api_key
        )
        return Success(data=result)
    else:
        result = await service.process_sync(
            session_id=params["session_id"],
            tenant_id=tenant_id,
            app_name=app_name,
            data=params["data"],
            dify_url=dify_url,
            dify_api_key=dify_api_key
        )
        return Success(data=result)


async def get_ai_fill_data_result_handler(
    request: Request,
    auth_info: dict
):
    """
    查询AI填单异步处理结果
    """
    params = await parse_request_params(request, AIFillDataResultRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    service = get_ai_fill_service()
    result = await service.get_result(
        session_id=params["session_id"],
        tenant_id=tenant_id,
        app_name=app_name
    )

    if not result:
        raise HTTPException(status_code=404, detail="Record not found")

    return Success(data=result)


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
    支持 response_mode 参数: sync(同步) 或 async(异步)
    """
    return await get_ai_fill_data_handler(request, auth_info)


@autofill_public_router.get("/autofill/get_ai_fill_data_result", summary="查询AI填单异步结果")
@autofill_public_router.post("/autofill/get_ai_fill_data_result", summary="查询AI填单异步结果")
async def get_ai_fill_data_result(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    查询AI填单异步处理结果
    支持 GET 和 POST 方法
    支持参数传递方式: Query / Form-Data / JSON Body
    """
    return await get_ai_fill_data_result_handler(request, auth_info)


# ==================== 字段组接口 ====================

async def get_field_group_handler(
    request: Request,
    auth_info: dict
):
    """
    查询字段组配置处理逻辑
    """
    from pydantic import BaseModel

    class FieldGroupRequest(BaseModel):
        page_code: Optional[str] = None
        group_code: Optional[str] = None
        group_name: Optional[str] = None

    params = await parse_request_params(request, FieldGroupRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    page_query = Q(tenant_id=tenant_id, app_name=app_name)
    if params.get("page_code"):
        page_query &= Q(page_code=params["page_code"])

    pages = await fill_page_controller.model.filter(page_query).all()
    page_ids = [p.id for p in pages]

    if not page_ids:
        return Success(data=[])

    q = Q(page_id__in=page_ids)
    if params.get("group_code"):
        q &= Q(group_code=params["group_code"])
    if params.get("group_name"):
        q &= Q(group_name__icontains=params["group_name"])

    field_groups = await field_group_config_controller.model.filter(q).all()

    return Success(data=[
        {
            "id": fg.id,
            "group_name": fg.group_name,
            "group_code": fg.group_code,
            "page_id": fg.page_id,
            "prompt_template_base": fg.prompt_template_base,
            "output_templates": fg.output_templates,
            "version": fg.version,
        }
        for fg in field_groups
    ])


@autofill_public_router.get("/autofill/field_group", summary="查询字段组配置")
@autofill_public_router.post("/autofill/field_group", summary="查询字段组配置")
async def get_field_group(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    根据app_name/page_name/字段组名或code查询字段组配置
    支持 GET 和 POST 方法
    支持参数传递方式: Query / Form-Data / JSON Body
    """
    return await get_field_group_handler(request, auth_info)


# ==================== 字段明细接口 ====================

async def list_field_spec_handler(
    request: Request,
    auth_info: dict
):
    """
    查询字段明细列表处理逻辑
    """
    from pydantic import BaseModel

    class FieldSpecListRequest(BaseModel):
        field_group_id: int

    params = await parse_request_params(request, FieldSpecListRequest)

    if not params.get("field_group_id"):
        raise HTTPException(status_code=400, detail="field_group_id is required")

    field_group = await field_group_config_controller.model.filter(
        id=params["field_group_id"]
    ).first()

    if not field_group:
        raise HTTPException(status_code=404, detail="Field group not found")

    page = await fill_page_controller.model.filter(
        id=field_group.page_id,
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"]
    ).first()

    if not page:
        raise HTTPException(status_code=403, detail="Access denied")

    field_specs = await field_spec_controller.get_by_field_group(params["field_group_id"])

    return Success(data=[
        {
            "id": fs.id,
            "field_group_id": fs.field_group_id,
            "field_name": fs.field_name,
            "field_label": fs.field_label,
            "field_type": fs.field_type,
            "fill_instruction": fs.fill_instruction,
            "options": fs.options,
            "corrections": fs.corrections,
            "is_active": fs.is_active,
        }
        for fs in field_specs
    ])


@autofill_public_router.get("/autofill/field_spec/list", summary="查询字段明细列表")
@autofill_public_router.post("/autofill/field_spec/list", summary="查询字段明细列表")
async def list_field_spec(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    查询字段组下的所有字段明细
    支持 GET 和 POST 方法
    支持参数传递方式: Query / Form-Data / JSON Body
    """
    return await list_field_spec_handler(request, auth_info)


# ==================== LLM 填单接口 ====================

async def llm_fill_handler(
    request: Request,
    auth_info: dict
):
    """
    直接LLM填单处理逻辑
    """
    from pydantic import BaseModel, Field

    class LLMFillRequest(BaseModel):
        field_group_id: Optional[int] = Field(None, description="字段组ID")
        field_group_code: Optional[str] = Field(None, description="字段组编码")
        input_data: Dict[str, Any] = {}

    params = await parse_request_params(request, LLMFillRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    field_group = None
    if params.get("field_group_id"):
        field_group = await field_group_config_controller.model.filter(
            id=params["field_group_id"]
        ).first()
    elif params.get("field_group_code"):
        field_group = await field_group_config_controller.model.filter(
            group_code=params["field_group_code"]
        ).first()
    else:
        raise HTTPException(status_code=400, detail="field_group_id or field_group_code is required")

    if not field_group:
        raise HTTPException(status_code=404, detail="Field group not found")

    page = await fill_page_controller.model.filter(
        id=field_group.page_id,
        tenant_id=tenant_id,
        app_name=app_name
    ).first()

    if not page:
        raise HTTPException(status_code=403, detail="Access denied")

    field_specs = await field_spec_controller.get_by_field_group(field_group.id, active_only=False)

    if not field_specs:
        raise HTTPException(status_code=404, detail="No fields found in this group")

    from app.services.prompt_service import build_function_schema
    from app.services.llm_proxy_service import llm_proxy_service
    from app.controllers.llm_config import llm_config_controller

    query = params.get("input_data", {}).get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="input_data.query is required")

    config = await llm_config_controller.get_default_config(
        tenant_id=tenant_id,
        app_name=app_name
    )

    if not config:
        raise HTTPException(status_code=500, detail="No LLM configuration found")

    tools = [build_function_schema(field_group, field_specs)]
    system_prompt = field_group.prompt_template_base or "你是一个智能填单助手。"

    try:
        result = await llm_proxy_service.process_request(
            query=query,
            tools=tools,
            system_prompt=system_prompt,
            tool_choice={"type": "function", "function": {"name": "extract_form_data"}},
            config=config
        )

        extracted_data = {k: v for k, v in result.items() if not k.startswith('_')}

        return Success(data={
            "field_group_id": field_group.id,
            "group_name": field_group.group_name,
            "group_code": field_group.group_code,
            "result": extracted_data,
            "_meta": result.get("_meta", {})
        })

    except ValueError as e:
        logger.error(f"LLM fill validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"LLM fill error: {e}")
        raise HTTPException(status_code=500, detail=f"LLM processing failed: {str(e)}")


@autofill_public_router.post("/autofill/llm/fill", summary="直接LLM填单")
async def llm_fill(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    直接调用LLM填单，返回JSON结果
    只支持 POST 方法
    支持参数传递方式: JSON Body
    """
    return await llm_fill_handler(request, auth_info)
