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

    # 2. 分析每个字段组的查询策略，避免后续重复判断
    # group_query_strategies: {group_name: {"type": "specified"|"full", "field_names": [...]}}
    group_query_strategies = {}
    specified_field_names = set()  # 所有指定了字段名的集合（用于批量查询）
    full_fetch_group_ids = []  # 需要查全量的字段组ID

    for fg in field_groups:
        if group_fields and fg.group_name in group_fields:
            group_field_names = group_fields[fg.group_name]
            if group_field_names:  # 指定了具体字段名
                group_query_strategies[fg.group_name] = {
                    "type": "specified",
                    "field_names": set(group_field_names),
                    "group_id": fg.id
                }
                specified_field_names.update(group_field_names)
            else:  # 空列表，需要查该组所有字段
                group_query_strategies[fg.group_name] = {
                    "type": "full",
                    "field_names": set(),
                    "group_id": fg.id
                }
                full_fetch_group_ids.append(fg.id)
        else:  # 没有指定字段，查所有字段组的所有字段
            group_query_strategies[fg.group_name] = {
                "type": "full",
                "field_names": set(),
                "group_id": fg.id
            }
            full_fetch_group_ids.append(fg.id)

    # 3. 查询字段明细（两种策略合并）
    all_field_specs_map = {}  # field_name -> field_spec

    # 策略1：通过 field_name + tenant_id + app_name 查询指定字段
    if specified_field_names:
        specified_field_list = list(specified_field_names)
        specified_fields = await field_spec_controller.model.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            field_name__in=specified_field_list,
            is_active=True
        ).all()
        
        for fs in specified_fields:
            all_field_specs_map[fs.field_name] = fs

    # 策略2：通过 field_group_id 查中间表，再查字段明细
    if full_fetch_group_ids:
        # 查询中间表获取所有 field_spec_id
        relations = await FieldGroupFieldSpec.filter(
            field_group_id__in=full_fetch_group_ids,
            tenant_id=tenant_id,
            app_name=app_name
        ).all()
        
        field_spec_ids = [r.field_spec_id for r in relations]
        
        if field_spec_ids:
            # 查询这些字段明细（通过 id in 查询）
            full_fetch_fields = await field_spec_controller.model.filter(
                id__in=field_spec_ids,
                tenant_id=tenant_id,
                app_name=app_name,
                is_active=True
            ).all()
            
            for fs in full_fetch_fields:
                # 避免重复添加（如果策略1已经查到了）
                if fs.field_name not in all_field_specs_map:
                    all_field_specs_map[fs.field_name] = fs

    # 4. 构建字段组与字段的映射关系（用于校验和分组）
    # 查询所有相关的中间表记录
    all_relations = await FieldGroupFieldSpec.filter(
        field_group_id__in=field_group_ids,
        tenant_id=tenant_id,
        app_name=app_name
    ).all()
    
    # 构建 field_group_id -> [field_spec_id] 的映射
    group_to_spec_ids = {}
    for r in all_relations:
        if r.field_group_id not in group_to_spec_ids:
            group_to_spec_ids[r.field_group_id] = []
        group_to_spec_ids[r.field_group_id].append(r.field_spec_id)

    # 构建 field_spec_id -> field_name 的映射
    spec_id_to_name = {fs.id: name for name, fs in all_field_specs_map.items()}

    field_groups_result = []
    all_field_specs = []
    all_properties = {}
    system_prompts = []

    for fg in field_groups:
        # 使用预计算的查询策略，避免重复判断
        strategy = group_query_strategies.get(fg.group_name, {})
        strategy_type = strategy.get("type", "full")
        
        # 确定该组需要哪些字段
        if strategy_type == "specified":
            # 指定了具体字段名
            target_field_names = strategy.get("field_names", set())
        else:
            # 需要该组所有字段（通过中间表关联）
            spec_ids = group_to_spec_ids.get(fg.id, [])
            target_field_names = {spec_id_to_name.get(sid) for sid in spec_ids}
            target_field_names = {name for name in target_field_names if name}

        # 从 all_field_specs_map 中获取该组的字段
        field_specs = []
        for field_name in target_field_names:
            fs = all_field_specs_map.get(field_name)
            if fs:
                field_specs.append(fs)

        # 检查是否需要跳过该字段组
        if strategy_type == "specified" and not field_specs:
            # 指定了字段但没找到，跳过该组
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
        # 1. 如果使用了 group_fields 并指定了具体字段名，只将这些字段设为 required
        # 2. 如果使用了 group_fields 但未指定字段名（查全量），所有字段设为 required
        # 3. 默认情况（查询所有字段），所有字段设为 required
        
        # 收集所有明确指定的字段名
        specified_field_names = set()
        for strategy in group_query_strategies.values():
            if strategy.get("type") == "specified":
                specified_field_names.update(strategy.get("field_names", set()))
        
        if specified_field_names:
            # 指定了具体字段名：只将这些字段设为 required
            filtered_properties = all_properties
            required_fields = list(specified_field_names & set(all_properties.keys()))
        else:
            # 查全量场景：所有字段设为 required
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
