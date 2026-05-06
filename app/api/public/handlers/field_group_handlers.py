"""
字段组相关接口
"""
import json
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException
from pydantic import BaseModel, Field
from tortoise.expressions import Q

from app.controllers.autofill import (
    field_group_config_controller,
    field_spec_controller,
    fill_page_controller,
)
from app.core.autofill_auth import APIKeyAuth
from app.core.request_parser import parse_request_params
from app.models.autofill import FieldGroupFieldSpec
from app.schemas.base import Success
from app.schemas.public import FieldGroupRequest
from app.services.autofill.prompt_service import (
    assemble_prompt,
    build_fields_instructions,
    build_function_schema,
)

router = APIRouter()


async def fetch_field_groups(
    tenant_id: int,
    app_name: str,
    page_name: str,
    group_names: List[str] = None,
    field_names: List[str] = None
) -> Dict[str, Any]:
    """
    查询字段组配置核心业务逻辑
    - 支持通过 page_name + group_names 查询多个字段组
    - 支持通过 field_names 筛选指定字段
    - 返回统一的 Function Calling Schema（可直接用于 LLM 调用）

    Returns:
        {
            "page_name": str,
            "field_groups": List[Dict],  # 各字段组明细
            "all_field_specs": List[Dict],  # 所有字段合并列表
            "unified_function_schema": Dict,  # 统一的 Function Calling Schema（可直接使用）
            "combined_prompt": str,  # 合并后的 Prompt
        }
    """
    group_names = group_names or []
    field_names = field_names or []

    page = await fill_page_controller.model.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        page_name=page_name
    ).first()

    if not page:
        return {
            "page_name": page_name,
            "field_groups": [],
            "all_field_specs": [],
            "unified_function_schema": None,
            "combined_prompt": "",
        }

    q = Q(tenant_id=tenant_id, app_name=app_name, page_id=page.id)
    if group_names:
        q &= Q(group_name__in=group_names)

    field_groups = await field_group_config_controller.model.filter(q).all()
    field_names_filter = set(field_names)

    field_groups_result = []
    all_field_specs = []
    all_properties = {}
    system_prompts = []

    for fg in field_groups:
        relations = await FieldGroupFieldSpec.filter(
            field_group_id=fg.id,
            tenant_id=tenant_id,
            app_name=app_name
        ).all()
        field_spec_ids = [r.field_spec_id for r in relations]

        field_specs = []
        if field_spec_ids:
            field_q = Q(id__in=field_spec_ids, is_active=True)
            if field_names_filter:
                field_q &= Q(field_name__in=list(field_names_filter))
            field_specs = await field_spec_controller.model.filter(field_q).all()

        if field_names_filter and not field_specs:
            continue

        # 收集所有字段
        for fs in field_specs:
            all_field_specs.append({
                "id": fs.id,
                "field_name": fs.field_name,
                "field_label": fs.field_label,
                "field_type": fs.field_type,
                "fill_instruction": fs.fill_instruction,
                "options": fs.options,
                "corrections": fs.corrections,
                "is_active": fs.is_active,
            })

        fields_instructions = build_fields_instructions(field_specs)
        function_schema = build_function_schema(fg, field_specs)
        example_query = "[用户对话内容将在这里插入]"
        assembled_prompt = assemble_prompt(fg, field_specs, example_query)

        # 合并 properties
        if function_schema:
            props = function_schema.get("function", {}).get("parameters", {}).get("properties", {})
            all_properties.update(props)

        # 收集 prompt
        if fg.prompt_template_base:
            system_prompts.append(fg.prompt_template_base)

        field_groups_result.append({
            "id": fg.id,
            "group_name": fg.group_name,
            "group_code": fg.group_code,
            "page_id": fg.page_id,
            "page_name": page.page_name if page else "",
            "prompt_template_base": fg.prompt_template_base,
            "output_templates": fg.output_templates or {},
            "version": fg.version,
            "is_active": fg.is_active,
            "description": fg.description,
            "field_specs": [
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
            "prompt_info": {
                "template_base": fg.prompt_template_base,
                "fields_instructions": fields_instructions,
                "assembled_prompt": assembled_prompt,
            },
            "function_calling": {
                "schema": function_schema,
                "json_schema": json.dumps(function_schema, ensure_ascii=False, indent=2),
            },
        })

    # 构建统一的 Function Calling Schema（可直接用于 LLM 调用）
    unified_function_schema = None
    if all_properties:
        unified_function_schema = {
            "type": "function",
            "function": {
                "name": "fill_form",
                "description": "从对话中提取表单数据",
                "parameters": {
                    "type": "object",
                    "properties": all_properties,
                    "required": list(all_properties.keys())
                }
            }
        }

    # 合并后的 Prompt
    combined_prompt = "\n\n".join(system_prompts) if system_prompts else "你是一个智能填单助手。"

    return {
        "page_name": page.page_name if page else page_name,
        "field_groups": field_groups_result,
        "all_field_specs": all_field_specs,
        "unified_function_schema": unified_function_schema,
        "combined_prompt": combined_prompt,
    }


async def get_field_group_handler(request: Request, auth_info: dict):
    """
    查询字段组配置处理逻辑（HTTP请求入口）
    """
    params = await parse_request_params(request, FieldGroupRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    result = await fetch_field_groups(
        tenant_id=tenant_id,
        app_name=app_name,
        page_name=params.get("page_name"),
        group_names=params.get("group_names", []),
        field_names=params.get("field_names", [])
    )

    # HTTP 接口返回字段组列表（保持兼容性）
    return Success(data=result.get("field_groups", []))


@router.get("/autofill/field_group", summary="查询字段组配置")
@router.post("/autofill/field_group", summary="查询字段组配置")
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
