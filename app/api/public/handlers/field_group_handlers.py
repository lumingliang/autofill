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
    group_fields: Dict[str, List[str]] = None
) -> Dict[str, Any]:
    """
    查询字段组配置核心业务逻辑（优化版本）
    
    设计说明：
    - 字段的唯一索引是 field_name + tenant_id + app_name
    - FieldGroupFieldSpec 仅用于管理字段组和字段的映射关系
    - 查询策略分为两种情况：
      1. 指定了字段名：直接用 field_name + tenant_id + app_name 查询字段明细
      2. 未指定字段名：通过 field_group_id 查中间表获取 field_spec_id，再查字段明细
    
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
    group_fields = group_fields or {}
    group_names = list(group_fields.keys())

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

    # 1. 查询字段组（通过 group_name in 查询）
    q = Q(tenant_id=tenant_id, app_name=app_name, page_id=page.id)
    if group_names:
        q &= Q(group_name__in=group_names)

    field_groups = await field_group_config_controller.model.filter(q).all()
    
    if not field_groups:
        return {
            "page_name": page_name,
            "field_groups": [],
            "all_field_specs": [],
            "unified_function_schema": None,
            "combined_prompt": "",
        }

    # 构建字段组ID到对象的映射
    field_group_map = {fg.id: fg for fg in field_groups}
    field_group_ids = list(field_group_map.keys())

    # 2. 收集查询条件，批量查询字段
    # group_query_info: {group_id: {"type": "specified"|"full", "field_names": set()|"field_spec_ids": set()}}
    group_query_info = {}
    all_specified_field_names = set()  # 所有指定字段名（用于批量查询）
    all_full_fetch_group_ids = []  # 需要查全量的字段组ID

    for fg in field_groups:
        group_field_names = group_fields.get(fg.group_name) if group_fields else None
        
        if group_field_names:  # 指定了具体字段名
            all_specified_field_names.update(group_field_names)
            group_query_info[fg.id] = {"type": "specified", "field_names": set(group_field_names)}
        else:  # 查全量
            all_full_fetch_group_ids.append(fg.id)
            group_query_info[fg.id] = {"type": "full"}

    # 批量查询所有字段（两种策略合并）
    all_field_specs_map = {}  # field_name -> field_spec

    # 策略1：通过 field_name 批量查询指定字段
    if all_specified_field_names:
        specified_fields = await field_spec_controller.model.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            field_name__in=list(all_specified_field_names),
            is_active=True
        ).all()
        for fs in specified_fields:
            all_field_specs_map[fs.field_name] = fs

    # 策略2：通过 field_group_id 批量查询全量字段
    # group_to_spec_ids: {group_id: [field_spec_id, ...]} - 用于后续字段分配
    group_to_spec_ids = {}
    if all_full_fetch_group_ids:
        # 批量查询中间表
        relations = await FieldGroupFieldSpec.filter(
            field_group_id__in=all_full_fetch_group_ids,
            tenant_id=tenant_id,
            app_name=app_name
        ).all()
        
        # 按字段组分组
        for r in relations:
            if r.field_group_id not in group_to_spec_ids:
                group_to_spec_ids[r.field_group_id] = []
            group_to_spec_ids[r.field_group_id].append(r.field_spec_id)
        
        # 批量查询所有字段明细
        all_spec_ids = [sid for ids in group_to_spec_ids.values() for sid in ids]
        if all_spec_ids:
            full_fetch_fields = await field_spec_controller.model.filter(
                id__in=all_spec_ids,
                tenant_id=tenant_id,
                app_name=app_name,
                is_active=True
            ).all()
            for fs in full_fetch_fields:
                all_field_specs_map[fs.field_name] = fs

    # 3. 组装字段组结果（直接使用已查询的数据）
    field_groups_result = []
    all_properties = {}
    system_prompts = []

    for fg in field_groups:
        query_info = group_query_info.get(fg.id, {})
        query_type = query_info.get("type", "full")
        
        # 根据查询类型获取字段
        if query_type == "specified":
            target_names = query_info.get("field_names", set())
            field_specs = [all_field_specs_map[name] for name in target_names if name in all_field_specs_map]
            # 如果指定了字段但没找到任何字段，跳过该组
            if not field_specs:
                continue
        else:
            spec_ids = set(group_to_spec_ids.get(fg.id, []))
            field_specs = [fs for fs in all_field_specs_map.values() if fs.id in spec_ids]

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

    # 从 all_field_specs_map 构建统一的字段列表（去重）
    all_field_specs = [
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
        for fs in all_field_specs_map.values()
    ]

    # 构建统一的 Function Calling Schema（可直接用于 LLM 调用）
    unified_function_schema = None
    if all_properties:
        # 智能确定 required 字段
        # 策略：
        # 1. 如果字段组是指定字段名类型，将该组的字段设为 required
        # 2. 查全量场景，所有字段设为 required
        
        has_specified = any(
            query_info.get("type") == "specified"
            for query_info in group_query_info.values()
        )
        
        if has_specified:
            # 有指定字段的组：只将指定字段设为 required
            specified_field_names = set()
            for fg_id, query_info in group_query_info.items():
                if query_info.get("type") == "specified":
                    target_names = query_info.get("field_names", set())
                    for name in target_names:
                        if name in all_field_specs_map:
                            specified_field_names.add(name)
            required_fields = list(specified_field_names & set(all_properties.keys()))
        else:
            # 查全量场景：所有字段设为 required
            required_fields = list(all_properties.keys())
        
        unified_function_schema = {
            "type": "function",
            "function": {
                "name": "fill_form",
                "description": "从对话中提取表单数据",
                "parameters": {
                    "type": "object",
                    "properties": all_properties,
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
        group_fields=params.get("group_fields", {})
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
