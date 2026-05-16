"""
LLM/AI 填单相关接口（优化版本）
全部采用POST路由，请求参数使用schema定义
"""
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException

from app.core.autofill_auth import APIKeyAuth
from app.core.request_parser import parse_request_params
from app.log import logger
from app.schemas.base import Success
from app.schemas.public import (
    AIFillDataRequest,
    AIFillDataResultRequest,
    LLMFillRequest,
    FieldGroupsSchemaRequest,
    OptimizeFieldInstructionRequest,
    StepLLMFillRequest,
    StepLLMFillResultRequest,
    ChatSessionRequest,
    TestFillRequest,
)
from app.services.autofill.llm_handler_service import (
    llm_fill_data_service,
    field_group_schema_service,
)
from app.services.autofill.field_optimization_service import field_optimization_service
from app.services.autofill.field_group_query_service import field_group_query_service
from app.services.llm.llm_proxy_service import llm_proxy_service
from app.services.autofill.step_llm_fill_service import step_llm_fill_service
from app.services.autofill.test_fill_service import test_fill_service

router = APIRouter(tags=["public"])


def _extract_field_value(field_data: Any) -> Any:
    """从 enriched 字段数据中提取值"""
    if field_data is None:
        return ""
    if isinstance(field_data, str):
        return field_data
    if isinstance(field_data, dict):
        if "value" in field_data:
            value = field_data["value"]
            if isinstance(value, dict):
                return value.get("value", "")
            if isinstance(value, list):
                return [v.get("value", v) if isinstance(v, dict) else v for v in value]
            return value
        return field_data
    return str(field_data)


def _enrich_extracted_data(extracted_data: Dict[str, Any], field_specs: List) -> Dict[str, Any]:
    """将 LLM 提取的数据 enriched 为包含完整选项信息的结构"""
    if not extracted_data or not field_specs:
        return extracted_data

    field_spec_map = {}
    for fs in field_specs:
        if isinstance(fs, dict):
            field_spec_map[fs.get("field_name")] = fs
        else:
            field_spec_map[fs.field_name] = fs

    enriched = {}

    for field_name, extracted_value in extracted_data.items():
        if field_name.endswith('_reason'):
            enriched[field_name] = extracted_value
            continue

        field_spec = field_spec_map.get(field_name)
        if not field_spec:
            enriched[field_name] = extracted_value
            continue

        if isinstance(field_spec, dict):
            field_type = field_spec.get("field_type", "")
            options = field_spec.get("options", {})
            field_label = field_spec.get("field_label", field_name)
        else:
            field_type = field_spec.field_type.value if hasattr(field_spec.field_type, 'value') else str(field_spec.field_type)
            options = field_spec.options
            field_label = getattr(field_spec, 'field_label', field_name)

        if field_type == 'text':
            enriched[field_name] = {"type": "text", "value": extracted_value, "label": field_label}
        elif field_type in ['select_single', 'select_multi']:
            items = [opt for opt in (options or {}).get('items', []) if not opt.get('is_deleted', False)]
            label_to_value = {opt['label']: opt.get('value', opt['label']) for opt in items}

            if field_type == 'select_single':
                label = extracted_value
                value = label_to_value.get(label, label)
                enriched[field_name] = {"type": "select_single", "value": {"value": value, "label": label}, "label": field_label}
            else:
                labels = extracted_value if isinstance(extracted_value, list) else [extracted_value]
                value_label_pairs = [{"value": label_to_value.get(label, label), "label": label} for label in labels]
                enriched[field_name] = {"type": "select_multi", "value": value_label_pairs, "label": field_label}
        else:
            enriched[field_name] = {"type": field_type, "value": extracted_value, "label": field_label}

    return enriched


def _process_output_templates(field_groups: List[Dict], enriched_result: Dict[str, Any]) -> Dict[str, Any]:
    """处理字段组的输出模板"""
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
            
            processed_template = template_content
            for field_name, field_data in enriched_result.items():
                placeholder1 = f"${{{field_name}}}"
                if placeholder1 in processed_template:
                    processed_template = processed_template.replace(placeholder1, str(_extract_display_value(field_data) or ""))
                
                placeholder2 = f"{{{{{field_name}}}}}"
                if placeholder2 in processed_template:
                    processed_template = processed_template.replace(placeholder2, str(_extract_display_value(field_data) or ""))
            
            result_key = f"{group_name}_{template_name}"
            output_templates_result[result_key] = {
                "template": processed_template,
                "description": template_config.get("description", "")
            }
    
    return output_templates_result


def _extract_display_value(field_data: Any) -> Any:
    """从 enriched 字段数据中提取显示值"""
    if not isinstance(field_data, dict):
        return field_data
    
    field_type = field_data.get("type", "")
    
    if field_type == "select_single":
        value_obj = field_data.get("value", {})
        if isinstance(value_obj, dict):
            return value_obj.get("label", value_obj.get("value", ""))
        return value_obj
    elif field_type == "select_multi":
        value_list = field_data.get("value", [])
        if isinstance(value_list, list):
            labels = [item.get("label", item.get("value", "")) for item in value_list if isinstance(item, dict)]
            return ", ".join(labels)
        return value_list
    elif field_type == "text":
        return field_data.get("value", "")
    else:
        return field_data.get("value", field_data)


# ==================== AI 填单接口 ====================

@router.post("/autofill/get_ai_fill_data", summary="获取AI填单数据")
async def get_ai_fill_data(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """三方应用调用: 接收请求 -> 存储数据 -> 转发Dify -> 返回响应"""
    params = await parse_request_params(request, AIFillDataRequest)
    
    result = await llm_fill_data_service.get_fill_data(
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"],
        session_id=params["session_id"],
        data=params["data"],
        page_name=params.get("page_name", ""),
        response_mode=params.get("response_mode", "sync")
    )
    
    return Success(data=result)


@router.post("/autofill/get_ai_fill_data_result", summary="查询AI填单异步结果")
async def get_ai_fill_data_result(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """查询 AI 填单异步处理结果"""
    params = await parse_request_params(request, AIFillDataResultRequest)
    
    result = await llm_fill_data_service.get_fill_result(
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"],
        session_id=params["session_id"]
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Record not found")
    
    return Success(data=result)


# ==================== 字段组 Schema 接口 ====================

@router.post("/autofill/field_groups/schema", summary="查询多个字段组的完整Schema")
async def get_field_groups_schema(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """查询多个字段组的完整 Schema 信息"""
    params = await parse_request_params(request, FieldGroupsSchemaRequest)
    
    result = await field_group_schema_service.get_field_groups_schema(
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"],
        page_name=params.get("page_name"),
        field_names=params.get("field_names"),
        group_names=params.get("group_names")
    )
    
    return Success(data=result)


# ==================== LLM 填单接口 ====================

async def _prepare_llm_fill_context(tenant_id: int, app_name: str, params: dict) -> tuple:
    """准备 LLM 填单的上下文数据"""
    from app.services.llm.llm_config_service import llm_config_service
    
    group_fields = params.get("group_fields", {}) or {}
    additional_data = params.get("additional_data", {}) or {}
    use_additional_data = params.get("use_additional_data", False)
    include_reason = params.get("include_reason", False)
    
    try:
        result_data = await field_group_query_service.fetch_field_groups(
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
    
    # 通过 service 层获取默认配置
    config = await llm_config_service.get_default_config()
    if not config:
        raise HTTPException(status_code=500, detail="No LLM configuration found")

    field_specs = result_data.get("all_field_specs", [])

    base_prompt = params.get("system_prompt") or result_data.get("combined_prompt", "你是一个智能填单助手。")

    # 下层会根据 tools 自动处理 format_instructions，直接使用 base_prompt
    if "{fields_instructions}" in base_prompt:
        system_prompt = base_prompt.replace("{fields_instructions}", "")
    else:
        system_prompt = base_prompt

    return result_data, config, system_prompt, field_specs, unified_function_schema, query


async def _execute_llm_fill(query: str, system_prompt: str, unified_function_schema: dict, config, field_specs: list, params: dict) -> dict:
    """执行 LLM 填单调用"""
    method = params.get("method")
    include_reason = params.get("include_reason", False)
    memory_rounds = params.get("memory_rounds", 0)
    session_id = params.get("session_id")
    
    return await llm_proxy_service.process_request(
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


async def _process_llm_result(llm_result: dict, field_specs: list, result_data: dict, params: dict) -> dict:
    """处理 LLM 结果"""
    method = params.get("method")
    extracted_data = {k: v for k, v in llm_result.items() if not k.startswith('_')}
    
    if method == "plain":
        return {"result": llm_result, "method": "plain", "_meta": llm_result.get("_meta", {})}
    
    additional_data = params.get("additional_data", {}) or {}
    use_additional_data = params.get("use_additional_data", False)
    if use_additional_data and additional_data:
        extracted_data = {**extracted_data, **additional_data}
    
    enriched_result = _enrich_extracted_data(extracted_data, field_specs)
    field_groups = result_data.get("field_groups", [])
    output_templates_result = _process_output_templates(field_groups, enriched_result)
    
    return {
        "result": enriched_result,
        "output_templates": output_templates_result,
        "_meta": llm_result.get("_meta", {})
    }


@router.post("/autofill/llm/fill", summary="直接LLM填单")
async def llm_fill(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """直接调用 LLM 填单，返回 JSON 结果"""
    params = await parse_request_params(request, LLMFillRequest)
    
    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]
    
    result_data, config, system_prompt, field_specs, unified_function_schema, query = \
        await _prepare_llm_fill_context(tenant_id, app_name, params)
    
    try:
        llm_result = await _execute_llm_fill(
            query=query,
            system_prompt=system_prompt,
            unified_function_schema=unified_function_schema,
            config=config,
            field_specs=field_specs,
            params=params
        )
        
        processed_result = await _process_llm_result(
            llm_result=llm_result,
            field_specs=field_specs,
            result_data=result_data,
            params=params
        )
        
        response_data = {
            "page_name": params.get("page_name"),
            "group_names": params.get("group_names", []),
            **processed_result
        }
        
        if processed_result.get("method") == "plain":
            response_data["_debug"] = {"system_prompt": system_prompt, "query": query}
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


# ==================== 分步 LLM 填单接口 ====================

async def _save_step_result(session_id: str, tenant_id: int, app_name: str, page_name: str, params: dict, llm_result: dict, enriched_result: dict, output_templates: dict, is_last: bool, elapsed_time: float = 0.0):
    """保存步骤结果"""
    method = params.get("method")
    group_fields = params.get("group_fields", {}) or {}
    query = params.get("query", "")
    
    llm_meta = llm_result.get("_meta", {})
    
    step_result = {
        "request": {
            "page_name": page_name,
            "group_fields": group_fields,
            "query": query,
            "method": method
        },
        "response": {
            "fields": list(enriched_result.keys()) if enriched_result else [],
            "fields_count": len(enriched_result) if enriched_result else 0
        },
        "raw_result": enriched_result if method != "plain" else llm_result,
        "extracted_fields": {k: _extract_field_value(v) for k, v in enriched_result.items()},
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
        step_data={"method": method, "fields_count": len(enriched_result) if enriched_result else 0, "elapsed_time": elapsed_time},
        is_last=is_last
    )


@router.post("/autofill/llm/fill/step", summary="分步LLM填单")
async def step_llm_fill(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """分步调用 LLM 填单，支持 session 管理和多轮数据存储"""
    import time
    
    params = await parse_request_params(request, StepLLMFillResultRequest)
    
    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]
    session_id = params.get("session_id")
    is_last = params.get("is_last", False)
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    
    session_info = await step_llm_fill_service.get_session_info(session_id)
    current_step = session_info["call_count"] + 1
    
    logger.info(f"Step LLM fill: session_id={session_id}, step={current_step}, is_last={is_last}")
    
    step_start_time = time.time()
    
    result_data, config, system_prompt, field_specs, unified_function_schema, query = \
        await _prepare_llm_fill_context(tenant_id, app_name, params)
    
    method = params.get("method")
    page_name = params.get("page_name")
    group_fields = params.get("group_fields", {}) or {}
    
    await step_llm_fill_service.save_step_request(
        session_id=session_id,
        tenant_id=tenant_id,
        app_name=app_name,
        page_name=page_name,
        request_data={
            "page_name": page_name,
            "group_fields": group_fields,
            "query": query,
            "method": method
        }
    )
    
    try:
        llm_result = await _execute_llm_fill(
            query=query,
            system_prompt=system_prompt,
            unified_function_schema=unified_function_schema,
            config=config,
            field_specs=field_specs,
            params=params
        )
        
        processed_result = await _process_llm_result(
            llm_result=llm_result,
            field_specs=field_specs,
            result_data=result_data,
            params=params
        )
        
        elapsed_time = time.time() - step_start_time
        
        enriched_result = processed_result.get("result", {})
        output_templates = processed_result.get("output_templates", {})
        
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
        await step_llm_fill_service.save_step_error(session_id=session_id, tenant_id=tenant_id, app_name=app_name, error_msg=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Step LLM fill error: {e}")
        await step_llm_fill_service.save_step_error(session_id=session_id, tenant_id=tenant_id, app_name=app_name, error_msg=str(e))
        raise HTTPException(status_code=500, detail=f"LLM processing failed: {str(e)}")


@router.post("/autofill/llm/fill/step/result", summary="获取分步填单结果")
async def get_step_llm_fill_result(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """获取分步填单的完整结果"""
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


# ==================== 字段优化接口 ====================

@router.post("/autofill/llm/optimize_instructions", summary="优化字段填写指引")
async def optimize_field_instructions(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """使用 LLM 优化字段填写指引"""
    params = await parse_request_params(request, OptimizeFieldInstructionRequest)
    
    result = await field_optimization_service.optimize_field_instructions(
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"],
        page_name=params.get("page_name"),
        group_name=params.get("group_name"),
        field_name=params.get("field_name"),
        batch_size=params.get("batch_size", 10),
        model=params.get("model")
    )
    
    return Success(data=result)


# ==================== 测试接口 ====================

@router.post("/autofill/llm/test/chat", summary="聊天会话")
async def chat_session(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """聊天会话接口，支持多轮对话"""
    params = await parse_request_params(request, ChatSessionRequest)
    
    result = await test_fill_service.chat_session(
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"],
        session_id=params.get("session_id"),
        system_prompt=params.get("system_prompt"),
        message=params.get("message", ""),
        clear_history=params.get("clear_history", False)
    )
    
    return Success(data=result)


@router.post("/autofill/llm/test/fill", summary="测试填单")
async def test_fill(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """测试填单功能"""
    params = await parse_request_params(request, TestFillRequest)
    
    result = await test_fill_service.test_fill(
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"],
        page_id=params.get("page_id"),
        group_fields=params.get("group_fields", {}),
        chat_record=params.get("chat_record", "")
    )
    
    return Success(data=result)
