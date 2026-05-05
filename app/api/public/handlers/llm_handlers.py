"""
LLM/AI 填单相关接口
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException
from pydantic import BaseModel, Field
from tortoise.expressions import Q

from app.controllers.autofill import (
    field_group_config_controller,
    field_spec_controller,
    fill_page_controller,
)
from app.controllers.llm_config import llm_config_controller
from app.core.autofill_auth import APIKeyAuth
from app.core.request_parser import parse_request_params
from app.log import logger
from app.models.autofill import FieldGroupFieldSpec
from app.schemas.autofill import AIFillDataRequest, AIFillDataResultRequest
from app.schemas.base import Success
from app.services.autofill.ai_fill_service import get_ai_fill_service
from app.services.autofill.prompt_service import (
    assemble_prompt,
    build_fields_instructions,
    build_function_schema,
)
from app.services.llm.llm_proxy_service import llm_proxy_service

router = APIRouter()


async def get_ai_fill_data_handler(request: Request, auth_info: dict):
    """获取AI填单数据处理逻辑，支持同步(sync)和异步(async)两种模式"""
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


async def get_ai_fill_data_result_handler(request: Request, auth_info: dict):
    """查询AI填单异步处理结果"""
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


@router.get("/autofill/get_ai_fill_data", summary="获取AI填单数据")
@router.post("/autofill/get_ai_fill_data", summary="获取AI填单数据")
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


@router.get("/autofill/get_ai_fill_data_result", summary="查询AI填单异步结果")
@router.post("/autofill/get_ai_fill_data_result", summary="查询AI填单异步结果")
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


def _build_field_param(field_spec):
    """构建单个字段的参数定义（符合 OpenAI Function Calling 规范）"""
    description = field_spec.fill_instruction or field_spec.field_label or field_spec.field_name

    param_info = {
        "type": "string",
        "description": description,
    }

    if field_spec.options and field_spec.options.get("items"):
        items = field_spec.options.get("items", [])
        valid_items = [item for item in items if not item.get("is_deleted", False)]
        if valid_items:
            param_info["enum"] = [item.get("label") for item in valid_items if item.get("label")]

            option_descs = []
            for item in valid_items[:10]:
                label = item.get("label", "")
                fill_inst = item.get("fill_instruction", "")
                if fill_inst:
                    option_descs.append(f"{label}: {fill_inst}")
                else:
                    option_descs.append(label)

            if option_descs:
                param_info["description"] = f"{description}。可选值：{', '.join(option_descs)}"
                if len(valid_items) > 10:
                    param_info["description"] += f" 等共{len(valid_items)}个选项"

    return param_info


def _build_function_schema(field_specs):
    """构建 Function Calling Schema"""
    function_schema = {
        "type": "function",
        "function": {
            "name": "fill_form",
            "description": "从对话中提取表单数据",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }

    for fs in field_specs:
        param_info = _build_field_param(fs)
        function_schema["function"]["parameters"]["properties"][fs.field_name] = param_info
        function_schema["function"]["parameters"]["required"].append(fs.field_name)

    return function_schema


def _merge_field_groups_config(field_groups):
    """合并多个字段组的配置"""
    merged = {
        "prompt_template_base": "",
        "output_templates": {},
        "description": ""
    }

    descriptions = []
    for fg in field_groups:
        # 取第一个非空的 template_base
        if not merged["prompt_template_base"] and fg.prompt_template_base:
            merged["prompt_template_base"] = fg.prompt_template_base

        # 合并 output_templates（后面的覆盖前面的）
        if fg.output_templates:
            merged["output_templates"].update(fg.output_templates)

        # 收集描述
        if fg.description:
            descriptions.append(fg.description)

    if descriptions:
        merged["description"] = "; ".join(descriptions)

    return merged


async def get_field_groups_schema_handler(request: Request, auth_info: dict):
    """
    查询字段组Schema信息（简化版）
    核心逻辑：确定字段组 -> 查询字段关联 -> 过滤字段 -> 合并输出
    """
    class FieldGroupsSchemaRequest(BaseModel):
        page_name: str = Field(..., description="页面名称（必填）")
        group_names: List[str] = Field(default_factory=list, description="字段组名称列表（可选）")
        field_names: List[str] = Field(default_factory=list, description="字段名称列表（可选）")

    params = await parse_request_params(request, FieldGroupsSchemaRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 1. 验证页面存在性
    page = await fill_page_controller.model.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        page_name=params.get("page_name")
    ).first()

    if not page:
        return Success(data={"fields": [], "merged_config": {}, "prompt_info": {}, "function_calling": {}})

    field_names_filter = set(params.get("field_names", []))
    group_names_filter = set(params.get("group_names", []))

    # 2. 确定查询的字段组（没传就用 default）
    if group_names_filter:
        field_groups = await field_group_config_controller.model.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            page_id=page.id,
            group_name__in=list(group_names_filter)
        ).all()
    else:
        field_groups = await field_group_config_controller.model.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            page_id=page.id,
            group_name="default"
        ).all()

    if not field_groups:
        return Success(data={"fields": [], "merged_config": {}, "prompt_info": {}, "function_calling": {}})

    # 3. 查询字段关联关系
    field_group_ids = [fg.id for fg in field_groups]
    relations_query = FieldGroupFieldSpec.filter(
        field_group_id__in=field_group_ids,
        tenant_id=tenant_id,
        app_name=app_name
    )

    # 如有 field_names，先查字段ID再过滤
    if field_names_filter:
        matching_specs = await field_spec_controller.model.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            field_name__in=list(field_names_filter),
            is_active=True
        ).all()
        matching_spec_ids = [fs.id for fs in matching_specs]
        relations_query = relations_query.filter(field_spec_id__in=matching_spec_ids)

    relations = await relations_query.all()
    field_spec_ids = list(set([r.field_spec_id for r in relations]))

    if not field_spec_ids:
        return Success(data={"fields": [], "merged_config": {}, "prompt_info": {}, "function_calling": {}})

    # 4. 批量查询字段明细
    field_specs = await field_spec_controller.model.filter(
        id__in=field_spec_ids,
        is_active=True
    ).all()

    if not field_specs:
        return Success(data={"fields": [], "merged_config": {}, "prompt_info": {}, "function_calling": {}})

    # 5. 合并字段组配置
    merged_config = _merge_field_groups_config(field_groups)

    # 6. 构建完整 Schema
    template_base = merged_config["prompt_template_base"] or """你是一个智能填单助手。请根据以下对话内容，提取指定字段的信息。

需要提取的字段：
{{fields_instructions}}

对话内容：
{{query}}

请严格按照字段要求提取信息，并以JSON格式返回结果。"""

    fields_instructions = build_fields_instructions(field_specs)
    assembled_prompt = assemble_prompt(
        type('obj', (object,), {'prompt_template_base': template_base})(),
        field_specs,
        "[用户对话内容将在这里插入]"
    )
    function_schema = _build_function_schema(field_specs)

    return Success(data={
        "fields": [
            {
                "id": fs.id,
                "field_name": fs.field_name,
                "field_label": fs.field_label,
                "field_type": fs.field_type,
                "fill_instruction": fs.fill_instruction,
                "options": fs.options,
                "corrections": fs.corrections,
                "is_active": fs.is_active,
            }
            for fs in field_specs
        ],
        "merged_config": merged_config,
        "prompt_info": {
            "template_base": template_base,
            "fields_instructions": fields_instructions,
            "assembled_prompt": assembled_prompt,
        },
        "function_calling": {
            "schema": function_schema,
            "json_schema": __import__('json').dumps(function_schema, ensure_ascii=False, indent=2),
        }
    })


@router.get("/autofill/field_groups/schema", summary="查询多个字段组的完整Schema")
@router.post("/autofill/field_groups/schema", summary="查询多个字段组的完整Schema")
async def get_field_groups_schema(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    查询多个字段组的完整Schema信息
    支持 GET 和 POST 方法
    支持参数传递方式: Query / Form-Data / JSON Body
    """
    return await get_field_groups_schema_handler(request, auth_info)


async def llm_fill_handler(request: Request, auth_info: dict):
    """直接LLM填单处理逻辑"""
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


@router.post("/autofill/llm/fill", summary="直接LLM填单")
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
