"""
字段组相关接口
全部采用POST路由，请求参数使用schema定义
"""
import json
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException
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


def _merge_system_prompts(system_prompts: List[str]) -> str:
    """
    智能合并多个字段组的 system prompt
    - 去重：移除重复的提示语
    - 优先级：保留最详细的提示
    - 格式化：统一格式，避免冲突
    """
    if not system_prompts:
        return "你是一个智能填单助手。"
    
    # 如果只有一个prompt，直接返回
    if len(system_prompts) == 1:
        return system_prompts[0]
    
    # 去重并保留顺序
    seen = set()
    unique_prompts = []
    for prompt in system_prompts:
        # 标准化：去除多余空白，用于比较
        normalized = " ".join(prompt.split())
        if normalized not in seen and prompt.strip():
            seen.add(normalized)
            unique_prompts.append(prompt)
    
    # 如果去重后只有一个，直接返回
    if len(unique_prompts) == 1:
        return unique_prompts[0]
    
    # 智能合并：提取共同部分，保留特殊要求
    # 策略：使用第一个作为主要prompt，其他的作为补充
    base_prompt = unique_prompts[0]
    additional_prompts = unique_prompts[1:]
    
    # 检查是否有冲突的指令，并合并
    merged_sections = []
    
    # 添加基础prompt
    merged_sections.append(base_prompt)
    
    # 添加其他prompt的补充说明
    for prompt in additional_prompts:
        # 提取prompt中的特殊要求（如果有）
        # 简化处理：直接添加，但标记来源
        if prompt not in base_prompt:  # 避免完全重复
            merged_sections.append(f"【补充要求】{prompt}")
    
    return "\n\n".join(merged_sections)


async def fetch_field_groups(
    tenant_id: int,
    app_name: str,
    page_name: str,
    group_names: List[str] = None,
    field_names: List[str] = None,
    group_fields: Dict[str, List[str]] = None
) -> Dict[str, Any]:
    """
    查询字段组配置核心业务逻辑
    - 支持通过 page_name + group_names 查询多个字段组
    - 支持通过 field_names 筛选指定字段（全局过滤）
    - 支持通过 group_fields 按字段组分别指定字段（优先级更高）
    - 返回统一的 Function Calling Schema（可直接用于 LLM 调用）

    Args:
        group_fields: 字段组与字段的映射关系，如 {"default": ["field1"], "group2": []}
                     空列表表示查询该组所有字段

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
    group_fields = group_fields or {}

    # 参数验证
    if not page_name:
        raise ValueError("page_name 不能为空")
    
    if not tenant_id or not app_name:
        raise ValueError("tenant_id 和 app_name 不能为空")

    page = await fill_page_controller.model.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        page_name=page_name
    ).first()

    if not page:
        raise ValueError(f"页面 '{page_name}' 不存在 (tenant_id={tenant_id}, app_name={app_name})")

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
            
            # 优先使用 group_fields 按字段组分别过滤
            if group_fields and fg.group_name in group_fields:
                group_field_names = group_fields[fg.group_name]
                if group_field_names:  # 如果指定了字段列表，则过滤
                    field_q &= Q(field_name__in=group_field_names)
                # 如果 group_field_names 是空列表，则不添加字段过滤，查询该组所有字段
            elif field_names_filter:
                # 使用全局 field_names 过滤
                field_q &= Q(field_name__in=list(field_names_filter))
            
            field_specs = await field_spec_controller.model.filter(field_q).all()

        # 检查是否需要跳过该字段组
        # 如果使用了 group_fields 且该组没有字段，则跳过
        # 如果使用了全局 field_names_filter 且没有匹配字段，则跳过
        if group_fields and fg.group_name in group_fields:
            # 使用 group_fields 模式
            group_field_names = group_fields[fg.group_name]
            if group_field_names and not field_specs:  # 指定了字段但没找到
                continue
            # 如果 group_field_names 是空列表，即使没有 field_specs 也不跳过（可能该组确实没有字段）
        elif field_names_filter and not field_specs:
            # 全局 field_names 模式
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
        # 智能确定 required 字段
        # 策略：
        # 1. 如果使用了 group_fields（分步填单场景），所有字段都设为 required
        #    因为用户明确指定了要查询的字段组，期望这些字段都有值
        # 2. 如果使用了 field_names（字段过滤场景），只将指定的字段设为 required
        #    其他字段虽然返回schema，但设为可选，允许LLM不返回
        # 3. 默认情况（查询所有字段），所有字段设为 required
        
        if group_fields:
            # 分步填单场景：使用 group_fields 时，all_properties 已经只包含需要的字段
            filtered_properties = all_properties
            required_fields = list(all_properties.keys())
        elif field_names_filter:
            # 字段过滤场景：只将明确指定的字段设为 required
            # 但保留其他字段的schema，设为可选
            filtered_properties = all_properties
            required_fields = list(field_names_filter & set(all_properties.keys()))
        else:
            # 默认场景：所有字段设为 required
            filtered_properties = all_properties
            required_fields = list(all_properties.keys())
        
        unified_function_schema = {
            "type": "function",
            "function": {
                "name": "fill_form",
                "description": "从对话中提取表单数据",
                "parameters": {
                    "type": "object",
                    "properties": filtered_properties,
                    "required": required_fields
                }
            }
        }

    # 合并后的 Prompt - 优化：去重并智能合并
    combined_prompt = _merge_system_prompts(system_prompts)

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

    # HTTP 接口返回字段组列表
    return Success(data=result.get("field_groups", []))


@router.post("/autofill/field_group", summary="查询字段组配置")
async def get_field_group(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    根据app_name/page_name/字段组名或code查询字段组配置
    只支持 POST 方法
    支持参数传递方式: JSON Body
    """
    return await get_field_group_handler(request, auth_info)
