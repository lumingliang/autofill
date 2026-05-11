"""
LLM/AI 填单相关接口
全部采用POST路由，请求参数使用schema定义
"""
import ast
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException
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
from app.models.autofill import FieldGroupFieldSpec, FillPage
from app.schemas.base import Success
from app.schemas.public import (
    AIFillDataRequest,
    AIFillDataResultRequest,
    LLMFillRequest,
    FieldGroupsSchemaRequest,
    OptimizeFieldInstructionRequest,
    StepLLMFillRequest,
    StepLLMFillResultRequest,
)
from app.services.autofill.ai_fill_service import get_ai_fill_service
from app.services.autofill.prompt_service import (
    build_fields_instructions,
    build_function_schema,
)
from app.services.llm.llm_proxy_service import llm_proxy_service
from app.services.llm.structured_output import StructuredOutputService
from app.services.autofill.step_llm_fill_service import step_llm_fill_service
from app.api.public.handlers.field_group_handlers import fetch_field_groups

router = APIRouter()


def _extract_field_value(field_data: Any) -> Any:
    """
    从enriched字段数据中提取值
    支持多种格式：字符串、字典、包含value的字典等
    """
    if field_data is None:
        return ""

    if isinstance(field_data, str):
        return field_data

    if isinstance(field_data, dict):
        # 如果是 enriched 格式，提取 value
        if "value" in field_data:
            value = field_data["value"]
            # 处理 select_single 格式 {"value": "xxx", "label": "yyy"}
            if isinstance(value, dict):
                return value.get("value", "")
            # 处理 select_multi 格式 [{"value": "xxx", "label": "yyy"}, ...]
            if isinstance(value, list):
                return [v.get("value", v) if isinstance(v, dict) else v for v in value]
            return value
        return field_data

    return str(field_data)


def _enrich_extracted_data(extracted_data: Dict[str, Any], field_specs: List) -> Dict[str, Any]:
    """
    将LLM提取的数据 enriched 为包含完整选项信息的结构
    
    输入: {"service_types": ["拖车服务", "送油服务"]}
    输出: {
        "service_types": {
            "type": "select_multi",
            "values": ["1", "4"],
            "labels": ["拖车服务", "送油服务"]
        }
    }
    """
    if not extracted_data or not field_specs:
        return extracted_data
    
    # 构建字段名到字段配置的映射
    # 兼容模型对象和 dict 两种格式
    field_spec_map = {}
    for fs in field_specs:
        if isinstance(fs, dict):
            field_spec_map[fs.get("field_name")] = fs
        else:
            field_spec_map[fs.field_name] = fs
    
    enriched = {}
    
    for field_name, extracted_value in extracted_data.items():
        # 处理理由字段（以 _reason 结尾）
        if field_name.endswith('_reason'):
            enriched[field_name] = extracted_value
            continue
        
        field_spec = field_spec_map.get(field_name)
        if not field_spec:
            # 如果找不到字段配置，保持原样
            enriched[field_name] = extracted_value
            continue
        
        # 兼容模型对象和 dict 两种格式
        if isinstance(field_spec, dict):
            field_type = field_spec.get("field_type", "")
            options = field_spec.get("options", {})
        else:
            field_type = field_spec.field_type.value if hasattr(field_spec.field_type, 'value') else str(field_spec.field_type)
            options = field_spec.options
        
        if field_type == 'text':
            # 文本类型：直接返回
            enriched[field_name] = {
                "type": "text",
                "value": extracted_value
            }
        
        elif field_type in ['select_single', 'select_multi']:
            # 下拉类型：需要映射label到value
            items = [opt for opt in (options or {}).get('items', []) 
                    if not opt.get('is_deleted', False)]
            
            # 构建label到value的映射
            label_to_value = {opt['label']: opt.get('value', opt['label']) for opt in items}
            
            if field_type == 'select_single':
                # 单选
                label = extracted_value
                value = label_to_value.get(label, label)
                enriched[field_name] = {
                    "type": "select_single",
                    "value": {"value": value, "label": label}
                }
            else:
                # 多选
                labels = extracted_value if isinstance(extracted_value, list) else [extracted_value]
                value_label_pairs = [
                    {"value": label_to_value.get(label, label), "label": label}
                    for label in labels
                ]
                enriched[field_name] = {
                    "type": "select_multi",
                    "value": value_label_pairs
                }
        else:
            # 其他类型：保持原样
            enriched[field_name] = extracted_value
    
    return enriched


def _process_output_templates(field_groups: List[Dict], enriched_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理字段组的输出模板，替换模板中的字段占位符
    
    Args:
        field_groups: 字段组列表，包含 output_templates 配置
        enriched_result: 提取并enriched后的字段结果
    
    Returns:
        字段组名称 -> 替换后的输出模板内容 的映射
        格式: {"字段组名称_模板名称": {"template": "替换后的模板内容", "description": "..."}}
    """
    output_templates_result = {}
    
    for fg in field_groups:
        group_name = fg.get("group_name", "")
        output_templates = fg.get("output_templates", {})
        
        if not output_templates or not isinstance(output_templates, dict):
            continue
        
        for template_name, template_config in output_templates.items():
            if not template_config or not isinstance(template_config, dict):
                continue
            
            template_content = template_config.get("template", "")
            if not template_content or not isinstance(template_content, str):
                continue
            
            # 替换模板中的字段占位符 ${field_name} 或 {{field_name}}
            processed_template = template_content
            for field_name, field_data in enriched_result.items():
                # 支持 ${field_name} 格式
                placeholder1 = f"${{{field_name}}}"
                if placeholder1 in processed_template:
                    display_value = _extract_display_value(field_data)
                    processed_template = processed_template.replace(placeholder1, str(display_value) if display_value is not None else "")
                
                # 支持 {{field_name}} 格式
                placeholder2 = f"{{{{{field_name}}}}}"
                if placeholder2 in processed_template:
                    display_value = _extract_display_value(field_data)
                    processed_template = processed_template.replace(placeholder2, str(display_value) if display_value is not None else "")
            
            # 使用 "字段组名称_模板名称" 作为key
            result_key = f"{group_name}_{template_name}"
            output_templates_result[result_key] = {
                "template": processed_template,
                "description": template_config.get("description", "")
            }
    
    return output_templates_result


def _extract_display_value(field_data: Any) -> Any:
    """
    从 enriched 字段数据中提取显示值
    
    对于下拉字段，返回 label
    对于文本字段，返回 value
    """
    if not isinstance(field_data, dict):
        return field_data
    
    field_type = field_data.get("type", "")
    
    if field_type == "select_single":
        # 单选: {"type": "select_single", "value": {"value": "...", "label": "..."}}
        value_obj = field_data.get("value", {})
        if isinstance(value_obj, dict):
            return value_obj.get("label", value_obj.get("value", ""))
        return value_obj
    
    elif field_type == "select_multi":
        # 多选: {"type": "select_multi", "value": [{"value": "...", "label": "..."}, ...]}
        value_list = field_data.get("value", [])
        if isinstance(value_list, list):
            labels = [item.get("label", item.get("value", "")) for item in value_list if isinstance(item, dict)]
            return ", ".join(labels)
        return value_list
    
    elif field_type == "text":
        # 文本: {"type": "text", "value": "..."}
        return field_data.get("value", "")
    
    else:
        # 其他类型，直接返回
        return field_data.get("value", field_data)


async def get_ai_fill_data_handler(request: Request, auth_info: dict):
    """获取AI填单数据处理逻辑，支持同步(sync)和异步(async)两种模式"""
    params = await parse_request_params(request, AIFillDataRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]
    dify_url = auth_info["dify_url"]
    dify_api_key = auth_info["dify_api_key"]

    # 如果传入了页面名称，优先使用页面配置的 Dify URL 和 API Key
    page_name = params.get("page_name", "")
    if page_name:
        page = await FillPage.filter(
            tenant_id=tenant_id,
            page_name=page_name,
            is_active=True
        ).first()
        if page and page.dify_agent_url and page.dify_api_key:
            dify_url = page.dify_agent_url
            dify_api_key = page.dify_api_key

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


@router.post("/autofill/get_ai_fill_data", summary="获取AI填单数据")
async def get_ai_fill_data(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    三方应用调用: 接收请求 -> 存储数据 -> 转发Dify -> 返回响应
    只支持 POST 方法
    支持参数传递方式: JSON Body
    """
    return await get_ai_fill_data_handler(request, auth_info)


@router.post("/autofill/get_ai_fill_data_result", summary="查询AI填单异步结果")
async def get_ai_fill_data_result(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    查询AI填单异步处理结果
    只支持 POST 方法
    支持参数传递方式: JSON Body
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
        },
        "function_calling": {
            "schema": function_schema,
            "json_schema": json.dumps(function_schema, ensure_ascii=False, indent=2),
        }
    })


@router.post("/autofill/field_groups/schema", summary="查询多个字段组的完整Schema")
async def get_field_groups_schema(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    查询多个字段组的完整Schema信息
    只支持 POST 方法
    支持参数传递方式: JSON Body
    """
    return await get_field_groups_schema_handler(request, auth_info)


async def _prepare_llm_fill_context(
    tenant_id: int,
    app_name: str,
    params: dict
) -> tuple:
    """
    准备LLM填单的上下文数据

    Returns:
        tuple: (result_data, config, system_prompt, field_specs, unified_function_schema, query)
    """
    group_fields = params.get("group_fields", {}) or {}
    additional_data = params.get("additional_data", {}) or {}
    use_additional_data = params.get("use_additional_data", False)
    include_reason = params.get("include_reason", False)

    # 调用 fetch_field_groups 获取字段组配置
    try:
        result_data = await fetch_field_groups(
            tenant_id=tenant_id,
            app_name=app_name,
            page_name=params.get("page_name"),
            group_fields=group_fields,
            additional_data=additional_data,
            use_additional_data=use_additional_data,
            include_reason=include_reason
        )
    except ValueError as e:
        logger.warning(f"fetch_field_groups validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"fetch_field_groups error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"获取字段配置失败: {str(e)}")

    unified_function_schema = result_data.get("unified_function_schema")
    if not unified_function_schema:
        raise HTTPException(status_code=404, detail="未找到有效的字段配置，请检查字段组是否存在且包含有效字段")

    query = params.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    config = await llm_config_controller.get_default_config(
        tenant_id=tenant_id,
        app_name=app_name
    )

    if not config:
        raise HTTPException(status_code=500, detail="No LLM configuration found")

    field_specs = result_data.get("all_field_specs", [])

    # 构建 system_prompt
    base_prompt = params.get("system_prompt") or result_data.get("combined_prompt", "你是一个智能填单助手。")

    if field_specs:
        fields_instructions = build_fields_instructions(field_specs)
        if "{fields_instructions}" in base_prompt:
            system_prompt = base_prompt.replace("{fields_instructions}", fields_instructions)
        else:
            system_prompt = f"""{base_prompt}

请根据以下字段指引从对话中提取信息：

{fields_instructions}

请严格按照字段要求提取信息。"""
    else:
        system_prompt = base_prompt

    return result_data, config, system_prompt, field_specs, unified_function_schema, query


async def _execute_llm_fill(
    query: str,
    system_prompt: str,
    unified_function_schema: dict,
    config,
    field_specs: list,
    params: dict
) -> dict:
    """
    执行LLM填单调用

    Returns:
        dict: LLM结果
    """
    method = params.get("method")
    include_reason = params.get("include_reason", False)
    memory_rounds = params.get("memory_rounds", 0)
    session_id = params.get("session_id")

    llm_result = await llm_proxy_service.process_request(
        query=query,
        tools=[unified_function_schema] if method != "plain" else None,
        system_prompt=system_prompt,
        tool_choice={"type": "function", "function": {"name": "fill_form"}},
        config=config,
        method=method,
        field_specs=field_specs,
        include_reason=include_reason,
        memory_rounds=memory_rounds,
        session_id=session_id
    )

    return llm_result


async def _process_llm_result(
    llm_result: dict,
    field_specs: list,
    result_data: dict,
    params: dict
) -> dict:
    """
    处理LLM结果，构建返回数据

    Returns:
        dict: 处理后的结果
    """
    method = params.get("method")
    extracted_data = {k: v for k, v in llm_result.items() if not k.startswith('_')}

    # plain 模式直接返回
    if method == "plain":
        return {
            "result": llm_result,
            "method": "plain",
            "_meta": llm_result.get("_meta", {})
        }

    # 合并附加数据
    additional_data = params.get("additional_data", {}) or {}
    use_additional_data = params.get("use_additional_data", False)
    if use_additional_data and additional_data:
        extracted_data = {**extracted_data, **additional_data}

    # enrich 数据
    enriched_result = _enrich_extracted_data(extracted_data, field_specs)

    # 处理输出模板
    field_groups = result_data.get("field_groups", [])
    output_templates_result = _process_output_templates(field_groups, enriched_result)

    return {
        "result": enriched_result,
        "output_templates": output_templates_result,
        "_meta": llm_result.get("_meta", {})
    }


async def llm_fill_handler(request: Request, auth_info: dict):
    """直接LLM填单处理逻辑"""
    params = await parse_request_params(request, LLMFillRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 准备上下文
    result_data, config, system_prompt, field_specs, unified_function_schema, query = \
        await _prepare_llm_fill_context(tenant_id, app_name, params)

    try:
        # 执行LLM调用
        llm_result = await _execute_llm_fill(
            query=query,
            system_prompt=system_prompt,
            unified_function_schema=unified_function_schema,
            config=config,
            field_specs=field_specs,
            params=params
        )

        # 处理结果
        processed_result = await _process_llm_result(
            llm_result=llm_result,
            field_specs=field_specs,
            result_data=result_data,
            params=params
        )

        # 构建最终响应
        response_data = {
            "page_name": params.get("page_name"),
            "group_names": params.get("group_names", []),
            **processed_result
        }

        # plain 模式添加调试信息
        if processed_result.get("method") == "plain":
            response_data["_debug"] = {
                "system_prompt": system_prompt,
                "query": query
            }
        else:
            response_data["_debug"] = {
                "system_prompt": system_prompt,
                "tools": [unified_function_schema],
                "tool_choice": {"type": "function", "function": {"name": "fill_form"}},
                "query": query
            }

        return Success(data=response_data)

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


async def _save_step_result(
    session_id: str,
    tenant_id: int,
    app_name: str,
    page_name: str,
    params: dict,
    llm_result: dict,
    enriched_result: dict,
    output_templates: dict,
    is_last: bool,
    elapsed_time: float = 0.0
):
    """保存步骤结果"""
    method = params.get("method")
    group_fields = params.get("group_fields", {}) or {}
    query = params.get("query", "")

    # 获取LLM元数据
    llm_meta = llm_result.get("_meta", {})

    # 构建步骤结果 - 简化存储，避免溢出
    step_result = {
        "request": {
            "page_name": page_name,
            "group_fields": group_fields,
            "query": query[:200] + "..." if len(query) > 200 else query,  # 限制query长度
            "method": method
        },
        "response": {
            # 只保存字段名称列表，不保存完整富化结果
            "fields": list(enriched_result.keys()) if enriched_result else [],
            "fields_count": len(enriched_result) if enriched_result else 0
        },
        # 保存原始格式（包含type和value的完整格式）
        "raw_result": enriched_result if method != "plain" else llm_result,
        # 保存提取的字段值（简化格式）
        "extracted_fields": {k: _extract_field_value(v) for k, v in enriched_result.items()},
        # 保存用时信息
        "timing": {
            "elapsed_time": elapsed_time,
            "llm_elapsed_time": llm_meta.get("elapsed_time"),
            "total_tokens": llm_meta.get("total_tokens"),
            "prompt_tokens": llm_meta.get("prompt_tokens"),
            "completion_tokens": llm_meta.get("completion_tokens")
        }
    }

    await step_llm_fill_service.save_step_result(
        session_id=session_id,
        tenant_id=tenant_id,
        app_name=app_name,
        page_name=page_name,
        step_result=step_result,
        is_last=is_last
    )

    await step_llm_fill_service.update_session_info(
        session_id=session_id,
        step_data={
            "method": method,
            "fields_count": len(enriched_result) if enriched_result else 0,
            "elapsed_time": elapsed_time
        },
        is_last=is_last
    )


async def step_llm_fill_handler(request: Request, auth_info: dict):
    """分步LLM填单处理逻辑"""
    import time

    params = await parse_request_params(request, StepLLMFillResultRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]
    session_id = params.get("session_id")
    is_last = params.get("is_last", False)

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    # 获取session信息
    session_info = await step_llm_fill_service.get_session_info(session_id)
    current_step = session_info["call_count"] + 1

    logger.info(f"Step LLM fill: session_id={session_id}, step={current_step}, is_last={is_last}")

    # 记录开始时间
    step_start_time = time.time()

    # 准备上下文
    result_data, config, system_prompt, field_specs, unified_function_schema, query = \
        await _prepare_llm_fill_context(tenant_id, app_name, params)

    method = params.get("method")
    page_name = params.get("page_name")
    group_fields = params.get("group_fields", {}) or {}

    # 立即记录请求数据（在LLM调用之前）
    await step_llm_fill_service.save_step_request(
        session_id=session_id,
        tenant_id=tenant_id,
        app_name=app_name,
        page_name=page_name,
        request_data={
            "page_name": page_name,
            "group_fields": group_fields,
            "query": query[:200] + "..." if len(query) > 200 else query,
            "method": method
        }
    )

    try:
        # 执行LLM调用
        llm_result = await _execute_llm_fill(
            query=query,
            system_prompt=system_prompt,
            unified_function_schema=unified_function_schema,
            config=config,
            field_specs=field_specs,
            params=params
        )

        # 处理结果
        processed_result = await _process_llm_result(
            llm_result=llm_result,
            field_specs=field_specs,
            result_data=result_data,
            params=params
        )

        # 计算用时
        elapsed_time = time.time() - step_start_time

        enriched_result = processed_result.get("result", {})
        output_templates = processed_result.get("output_templates", {})

        # 保存步骤结果（更新结果数据）
        await _save_step_result(
            session_id=session_id,
            tenant_id=tenant_id,
            app_name=app_name,
            page_name=page_name,
            params=params,
            llm_result=llm_result,
            enriched_result=enriched_result if method != "plain" else {},
            output_templates=output_templates if method != "plain" else {},
            is_last=is_last,
            elapsed_time=elapsed_time
        )

        # 构建响应
        response_data = {
            "session_id": session_id,
            "step": current_step,
            "is_last": is_last,
            "status": "completed" if is_last else "processing",
            "page_name": page_name,
            "group_names": params.get("group_names", []),
            "elapsed_time": elapsed_time,
            **processed_result
        }

        # 最后一步返回合并后的字段
        if is_last and method != "plain":
            final_result = await step_llm_fill_service.get_step_result(
                session_id=session_id,
                tenant_id=tenant_id,
                app_name=app_name
            )
            response_data["merged_fields"] = final_result.get("merged_fields", {}) if final_result else {}

        return Success(data=response_data)

    except ValueError as e:
        logger.error(f"Step LLM fill validation error: {e}")
        # 记录错误状态
        await step_llm_fill_service.save_step_error(
            session_id=session_id,
            tenant_id=tenant_id,
            app_name=app_name,
            error_msg=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Step LLM fill error: {e}")
        # 记录错误状态
        await step_llm_fill_service.save_step_error(
            session_id=session_id,
            tenant_id=tenant_id,
            app_name=app_name,
            error_msg=str(e)
        )
        raise HTTPException(status_code=500, detail=f"LLM processing failed: {str(e)}")


@router.post("/autofill/llm/fill/step", summary="分步LLM填单")
async def step_llm_fill(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    分步调用LLM填单，支持session管理和多轮数据存储
    只支持 POST 方法
    支持参数传递方式: JSON Body

    特点：
    - 通过 session_id 标识同一轮填单流程
    - 自动记录调用次数和每轮结果
    - is_last=true 时结束填单流程并返回完整结果
    - 所有步骤的数据和结果都保存到数据库
    """
    return await step_llm_fill_handler(request, auth_info)


@router.post("/autofill/llm/fill/step/result", summary="获取分步填单结果")
async def get_step_llm_fill_result(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    获取分步填单的完整结果
    只支持 POST 方法
    支持参数传递方式: JSON Body

    请求参数：
    - session_id: 会话ID（必填）
    """
    params = await parse_request_params(request, StepLLMFillResultRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]
    session_id = params.get("session_id")

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    result = await step_llm_fill_service.get_step_result(
        session_id=session_id,
        tenant_id=tenant_id,
        app_name=app_name
    )

    if not result:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return Success(data=result)


async def optimize_field_instructions_handler(request: Request, auth_info: dict):
    """优化字段填写指引处理逻辑"""
    params = await parse_request_params(request, OptimizeFieldInstructionRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]
    page_name = params.get("page_name")
    group_name = params.get("group_name")
    field_name = params.get("field_name")
    batch_size = params.get("batch_size", 10)

    # 1. 查找页面
    page = await fill_page_controller.model.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        page_name=page_name
    ).first()

    if not page:
        raise HTTPException(status_code=404, detail=f"Page '{page_name}' not found")

    # 2. 构建查询条件
    field_q = Q(tenant_id=tenant_id, app_name=app_name, is_active=True)

    if field_name:
        # 优化单个字段
        field_q &= Q(field_name=field_name)
    else:
        # 查询字段组或页面下的所有字段
        if group_name:
            # 查找指定字段组
            field_group = await field_group_config_controller.model.filter(
                tenant_id=tenant_id,
                app_name=app_name,
                page_id=page.id,
                group_name=group_name
            ).first()

            if not field_group:
                raise HTTPException(status_code=404, detail=f"Field group '{group_name}' not found")

            # 获取字段组关联的字段ID
            relations = await FieldGroupFieldSpec.filter(
                field_group_id=field_group.id,
                tenant_id=tenant_id,
                app_name=app_name
            ).all()
            field_spec_ids = [r.field_spec_id for r in relations]

            if not field_spec_ids:
                return Success(data={"optimized_count": 0, "results": []})

            field_q &= Q(id__in=field_spec_ids)
        else:
            # 查询页面下所有字段组关联的字段
            field_groups = await field_group_config_controller.model.filter(
                tenant_id=tenant_id,
                app_name=app_name,
                page_id=page.id
            ).all()

            if not field_groups:
                return Success(data={"optimized_count": 0, "results": []})

            field_group_ids = [fg.id for fg in field_groups]
            relations = await FieldGroupFieldSpec.filter(
                field_group_id__in=field_group_ids,
                tenant_id=tenant_id,
                app_name=app_name
            ).all()
            field_spec_ids = list(set([r.field_spec_id for r in relations]))

            if not field_spec_ids:
                return Success(data={"optimized_count": 0, "results": []})

            field_q &= Q(id__in=field_spec_ids)

    # 3. 查询需要优化的字段
    field_specs = await field_spec_controller.model.filter(field_q).all()

    if not field_specs:
        return Success(data={"optimized_count": 0, "results": []})

    # 4. 分批处理
    config = await llm_config_controller.get_default_config(
        tenant_id=tenant_id,
        app_name=app_name
    )

    if not config:
        raise HTTPException(status_code=500, detail="No LLM configuration found")

    # 使用指定的模型（如果有）
    if params.get("model"):
        config.model = params["model"]

    results = []
    total_count = len(field_specs)

    # 分批处理
    for i in range(0, total_count, batch_size):
        batch = field_specs[i:i + batch_size]
        batch_results = await _optimize_field_batch(
            tenant_id=tenant_id,
            app_name=app_name,
            fields=batch,
            config=config
        )
        results.extend(batch_results)

    return Success(data={
        "optimized_count": len([r for r in results if r["success"]]),
        "total_count": total_count,
        "results": results
    })


async def _optimize_field_batch(tenant_id: int, app_name: str, fields: list, config: Any) -> list:
    """
    优化一批字段的填写指引
    
    使用结构化输出一次性处理多个字段，提高效率
    """
    results = []
    
    if not fields:
        return results
    
    # 创建结构化输出服务
    service = StructuredOutputService(config)
    
    # 构建字段信息列表
    fields_info = []
    for field in fields:
        field_type = field.field_type.value if field.field_type else "text"
        field_info = {
            "field_name": field.field_name,
            "field_label": field.field_label or field.field_name,
            "field_type": field_type,
            "current_instruction": field.fill_instruction or "",
            "options": field.options.get("items", []) if field.options and field_type in ["select_single", "select_multi"] else []
        }
        fields_info.append(field_info)
    
    # 构建字段名列表（用于提示词）
    field_names_list = [f["field_name"] for f in fields_info]
    fields_text = json.dumps(fields_info, ensure_ascii=False, indent=2)
    
    # 构建 Function Calling Schema - 使用扁平化结构，每个字段一个参数
    # 这样 LLM 更容易理解：参数名就是 field_name，参数值就是 optimized_instruction
    properties = {}
    for field_info in fields_info:
        field_name = field_info["field_name"]
        properties[field_name] = {
            "type": "string",
            "description": f"优化后的填写指引（原指引：{field_info['current_instruction'][:50] if field_info['current_instruction'] else '无'}...）"
        }
    
    function_schema = {
        "type": "function",
        "function": {
            "name": "optimize_field_instructions",
            "description": f"优化以下字段的填写指引：{', '.join(field_names_list)}",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(properties.keys())
            }
        }
    }
    
    # 构建提示词
    prompt = f"""你是一个专业的表单设计专家。请优化以下字段的填写指引。

需要优化的字段列表：
{fields_text}

优化要求：
1. 清晰描述每个字段的用途和填写要求
2. 对于下拉选择字段，说明如何选择合适的选项，包含常见场景的判断逻辑
3. 对于文本字段，说明应该提取什么样的信息，包含常见格式的示例
4. 使用简洁专业的语言
5. 保持原有指引的核心信息，但使其更加清晰和易于理解
6. **重要**：optimize_field_instructions 函数的每个参数名对应一个字段名，参数值为该字段优化后的填写指引

请调用 optimize_field_instructions 函数，为每个字段返回优化后的填写指引。"""

    try:
        # 调用LLM，使用 bind_tools_non_stream 方法获取结构化输出
        result = await service.generate(
            query=prompt,
            tools=[function_schema],
            system_prompt="你是一个专业的表单设计专家，擅长编写清晰、准确的字段填写指引。",
            tool_choice={"type": "function", "function": {"name": "optimize_field_instructions"}},
            method="bind_tools_non_stream"
        )
        
        if not result.success:
            raise ValueError(f"Failed to generate: {result.error}")
        
        # 调试：打印完整返回结果
        logger.info(f"[DEBUG] result.data: {result.data}")
        logger.info(f"[DEBUG] result.method: {result.method}")
        
        # 解析优化结果 - result.data 直接就是 {field_name: instruction, ...}
        optimized_map = result.data
        
        # 更新每个字段的指引
        for field in fields:
            field_label = field.field_label or field.field_name
            current_instruction = field.fill_instruction or ""
            
            if field.field_name in optimized_map:
                optimized_instruction = optimized_map[field.field_name].strip()
                
                if optimized_instruction:
                    # 更新字段指引
                    await field_spec_controller.update(
                        id=field.id,
                        obj_in={"fill_instruction": optimized_instruction}
                    )
                    
                    results.append({
                        "field_name": field.field_name,
                        "field_label": field_label,
                        "success": True,
                        "original_instruction": current_instruction,
                        "optimized_instruction": optimized_instruction
                    })
                else:
                    results.append({
                        "field_name": field.field_name,
                        "field_label": field_label,
                        "success": False,
                        "error": "LLM returned empty instruction"
                    })
            else:
                results.append({
                    "field_name": field.field_name,
                    "field_label": field_label,
                    "success": False,
                    "error": f"Field not found in LLM response. Available: {list(optimized_map.keys())}"
                })
    
    except Exception as e:
        logger.error(f"Failed to optimize batch: {e}")
        # 批量失败时，为所有字段记录失败
        for field in fields:
            results.append({
                "field_name": field.field_name,
                "field_label": field.field_label or field.field_name,
                "success": False,
                "error": str(e)
            })
    
    return results


@router.post("/autofill/llm/optimize_instructions", summary="优化字段填写指引")
async def optimize_field_instructions(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    使用LLM优化字段填写指引
    支持批量处理，每批默认10个字段
    只支持 POST 方法
    支持参数传递方式: JSON Body
    """
    return await optimize_field_instructions_handler(request, auth_info)
