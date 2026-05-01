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
                                      field_group_config_controller,
                                      field_spec_controller,
                                      fill_data_record_controller,
                                      fill_page_controller,
                                      summary_template_controller)
from app.core.autofill_auth import APIKeyAuth
from app.core.request_parser import parse_request_params
from app.schemas.base import Fail, Success
from app.schemas.autofill import *
from app.services.ai_fill_service import get_ai_fill_service
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
    支持同步(sync)和异步(async)两种模式
    """
    # 使用通用参数解析组件获取参数
    params = await parse_request_params(request, AIFillDataRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]
    dify_url = auth_info["dify_url"]
    dify_api_key = auth_info["dify_api_key"]

    if not dify_url or not dify_api_key:
        raise HTTPException(status_code=500, detail="Dify configuration not found")

    # 获取服务实例
    service = get_ai_fill_service()

    # 根据响应模式选择处理方式
    response_mode = params.get("response_mode", "sync")

    if response_mode == "async":
        # 异步模式：将请求发送到 Kafka 队列
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
        # 同步模式：直接调用 Dify
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
    # 使用通用参数解析组件获取参数
    params = await parse_request_params(request, AIFillDataResultRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 获取服务实例
    service = get_ai_fill_service()

    # 查询结果
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


# ==================== 智能填单系统新接口 ====================

async def get_field_group_handler(
    request: Request,
    auth_info: dict
):
    """
    查询字段组配置处理逻辑
    支持根据 app_name/page_name/字段组名或code查询
    """
    from pydantic import BaseModel

    class FieldGroupRequest(BaseModel):
        page_code: Optional[str] = None
        group_code: Optional[str] = None
        group_name: Optional[str] = None

    params = await parse_request_params(request, FieldGroupRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 先查询页面
    page_query = Q(tenant_id=tenant_id, app_name=app_name)
    if params.get("page_code"):
        page_query &= Q(page_code=params["page_code"])

    pages = await fill_page_controller.model.filter(page_query).all()
    page_ids = [p.id for p in pages]

    if not page_ids:
        return Success(data=[])

    # 查询字段组
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


async def list_field_spec_handler(
    request: Request,
    auth_info: dict
):
    """
    查询字段明细列表处理逻辑
    查询字段组下的所有字段明细
    """
    from pydantic import BaseModel

    class FieldSpecListRequest(BaseModel):
        field_group_id: int

    params = await parse_request_params(request, FieldSpecListRequest)

    if not params.get("field_group_id"):
        raise HTTPException(status_code=400, detail="field_group_id is required")

    # 验证字段组是否存在且属于当前租户
    field_group = await field_group_config_controller.model.filter(
        id=params["field_group_id"]
    ).first()

    if not field_group:
        raise HTTPException(status_code=404, detail="Field group not found")

    # 验证页面权限
    page = await fill_page_controller.model.filter(
        id=field_group.page_id,
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"]
    ).first()

    if not page:
        raise HTTPException(status_code=403, detail="Access denied")

    # 查询字段明细
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


async def llm_fill_handler(
    request: Request,
    auth_info: dict
):
    """
    直接LLM填单处理逻辑
    使用LLMProxy服务完成填单，支持Function Calling和结构化输出
    支持通过 field_group_id 或 field_group_code 指定字段组
    """
    from pydantic import BaseModel, Field
    from typing import Union

    class LLMFillRequest(BaseModel):
        field_group_id: Optional[int] = Field(None, description="字段组ID")
        field_group_code: Optional[str] = Field(None, description="字段组编码（唯一标识）")
        input_data: Dict[str, Any] = {}

    params = await parse_request_params(request, LLMFillRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 获取字段组配置 - 支持通过 ID 或 Code 查询
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

    # 验证页面权限
    page = await fill_page_controller.model.filter(
        id=field_group.page_id,
        tenant_id=tenant_id,
        app_name=app_name
    ).first()

    if not page:
        raise HTTPException(status_code=403, detail="Access denied")

    # 获取字段明细（获取所有字段，包括禁用的，用于LLM填单）
    field_specs = await field_spec_controller.get_by_field_group(field_group.id, active_only=False)

    if not field_specs:
        raise HTTPException(status_code=404, detail="No fields found in this group")

    # 构建Function Calling Schema
    from app.services.prompt_service import build_function_schema, assemble_prompt
    from app.services.llm_proxy_service import llm_proxy_service
    from app.controllers.llm_config import llm_config_controller

    query = params.get("input_data", {}).get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="input_data.query is required")

    # 获取LLM配置
    config = await llm_config_controller.get_default_config(
        tenant_id=tenant_id,
        app_name=app_name
    )

    if not config:
        raise HTTPException(status_code=500, detail="No LLM configuration found")

    # 构建tools（Function Calling Schema）
    tools = [build_function_schema(field_group, field_specs)]

    # 构建system_prompt
    system_prompt = field_group.prompt_template_base or """你是一个智能填单助手。请根据用户提供的对话内容，提取指定字段的信息并以结构化格式返回。"""

    try:
        # 使用LLMProxy服务处理请求
        result = await llm_proxy_service.process_request(
            query=query,
            tools=tools,
            system_prompt=system_prompt,
            tool_choice={"type": "function", "function": {"name": "extract_form_data"}},
            config=config
        )

        # 提取填单结果
        # result 直接包含提取的字段数据，不是包装在 extract_form_data 键下
        # 需要移除 _meta 键，剩下的就是提取的数据
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


async def update_field_spec_handler(
    request: Request,
    auth_info: dict
):
    """
    更新字段配置处理逻辑
    更新指定字段组的字段配置
    """
    from pydantic import BaseModel, Field

    class UpdateFieldSpecRequest(BaseModel):
        id: int
        field_label: Optional[str] = None
        fill_instruction: Optional[str] = None
        options: Optional[Dict[str, Any]] = None
        corrections: Optional[List[Dict[str, Any]]] = None
        is_active: Optional[bool] = None

    class UpdateFieldSpecBatchRequest(BaseModel):
        field_group_id: int
        fields: List[UpdateFieldSpecRequest]

    params = await parse_request_params(request, UpdateFieldSpecBatchRequest)

    if not params.get("field_group_id"):
        raise HTTPException(status_code=400, detail="field_group_id is required")

    if not params.get("fields"):
        raise HTTPException(status_code=400, detail="fields is required")

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 验证字段组是否存在
    field_group = await field_group_config_controller.model.filter(
        id=params["field_group_id"]
    ).first()

    if not field_group:
        raise HTTPException(status_code=404, detail="Field group not found")

    # 验证页面权限
    page = await fill_page_controller.model.filter(
        id=field_group.page_id,
        tenant_id=tenant_id,
        app_name=app_name
    ).first()

    if not page:
        raise HTTPException(status_code=403, detail="Access denied")

    # 更新字段配置
    updated_count = 0
    errors = []

    for field_data in params["fields"]:
        field_id = field_data.get("id")
        if not field_id:
            errors.append({"error": "Field id is required", "data": field_data})
            continue

        # 验证字段是否属于该字段组
        field_spec = await field_spec_controller.model.filter(
            id=field_id,
            field_group_id=params["field_group_id"]
        ).first()

        if not field_spec:
            errors.append({"error": f"Field {field_id} not found in this group", "id": field_id})
            continue

        # 构建更新数据
        update_data = {}
        if "field_label" in field_data:
            update_data["field_label"] = field_data["field_label"]
        if "fill_instruction" in field_data:
            update_data["fill_instruction"] = field_data["fill_instruction"]
        if "options" in field_data:
            update_data["options"] = field_data["options"]
        if "corrections" in field_data:
            update_data["corrections"] = field_data["corrections"]
        if "is_active" in field_data:
            update_data["is_active"] = field_data["is_active"]

        if update_data:
            try:
                # 直接更新模型字段
                for key, value in update_data.items():
                    setattr(field_spec, key, value)
                await field_spec.save()
                updated_count += 1
            except Exception as e:
                errors.append({"error": str(e), "id": field_id})

    return Success(data={
        "updated_count": updated_count,
        "total_count": len(params["fields"]),
        "errors": errors if errors else None
    })


@autofill_public_router.post("/autofill/field_spec/update", summary="更新字段配置")
async def update_field_spec(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    更新指定字段组的字段配置
    只支持 POST 方法
    支持参数传递方式: JSON Body
    """
    return await update_field_spec_handler(request, auth_info)
