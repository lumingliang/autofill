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
    StepLLMFillResponse,
    ChatSessionRequest,
    TestFillRequest,
)
from app.services.autofill.llm_handler_service import (
    llm_fill_data_service,
    field_group_schema_service,
)
from app.services.autofill.field_optimization_service import field_optimization_service
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


def _simplify_field_structure(fields: Dict[str, Any]) -> Dict[str, Any]:
    """简化字段结构，将嵌套的 value 对象扁平化
    
    原始结构: {"field_name": {"type": "select_single", "value": {"value": "EVT001", "label": "道路救援"}, "label": "一级事件类型"}}
    简化后: {"field_name": {"type": "select_single", "value": "EVT001", "label": "道路救援"}}
    
    多选类型返回数组结构:
    {"field_name": {"type": "select_multi", "value": ["val1", "val2"], "labels": ["标签1", "标签2"]}}
    """
    if not fields:
        return {}
    
    simplified = {}
    for field_name, field_data in fields.items():
        if not isinstance(field_data, dict):
            simplified[field_name] = field_data
            continue
            
        field_type = field_data.get("type", "")
        value = field_data.get("value")
        label = field_data.get("label", field_name)
        
        # 处理 select_single 类型：提取 value 和 label
        if field_type == "select_single" and isinstance(value, dict):
            simplified[field_name] = {
                "type": field_type,
                "value": value.get("value", ""),
                "label": value.get("label", "")
            }
        # 处理 select_multi 类型：返回数组结构
        elif field_type == "select_multi" and isinstance(value, list):
            values = []
            labels = []
            for v in value:
                if isinstance(v, dict):
                    values.append(v.get("value", v))
                    labels.append(v.get("label", v.get("value", v)))
                else:
                    values.append(v)
                    labels.append(str(v))
            simplified[field_name] = {
                "type": field_type,
                "value": values,
                "labels": labels
            }
        # 其他类型保持原样
        else:
            simplified[field_name] = field_data
            
    return simplified


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


def _process_output_templates(field_groups: List[Dict], enriched_result: Dict[str, Any]) -> Dict[str, str]:
    """处理字段组的输出模板
    
    返回格式: {"group_name": "变量替换后的字符串"}
    只处理每个字段组的 default 模板
    """
    output_templates_result = {}

    for fg in field_groups:
        group_name = fg.get("group_name", "")
        output_templates = fg.get("output_templates", {})

        if not output_templates or not isinstance(output_templates, dict):
            continue

        # 只处理 default 模板
        template_config = output_templates.get("default")
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

        output_templates_result[group_name] = processed_template

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
        field_names=params.get("field_names"),
        group_names=params.get("group_names")
    )

    return Success(data=result)


# ==================== LLM 填单接口 ====================

@router.post("/autofill/llm/fill", summary="直接LLM填单")
async def llm_fill(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """直接调用 LLM 填单，返回 JSON 结果"""
    params = await parse_request_params(request, LLMFillRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    try:
        # 调用 service 层方法（复用核心逻辑）
        result = await step_llm_fill_service.execute_llm_fill(
            tenant_id=tenant_id,
            app_name=app_name,
            field_names=params.get("field_names", []),
            group_names=params.get("group_names", []),
            system_prompt_group=params.get("system_prompt_group"),
            query=params.get("query", ""),
            method=params.get("method"),
            system_prompt=params.get("system_prompt"),
            additional_data=params.get("additional_data"),
            use_additional_data=params.get("use_additional_data", False),
            include_reason=params.get("include_reason", False),
            memory_rounds=params.get("memory_rounds", 0)
        )

        # 简化字段结构，移除嵌套的 value 对象
        simplified_fields = _simplify_field_structure(result.get("result", {}))
        
        response_data = {
            "app_name": app_name,
            "group_names": params.get("group_names", []),
            "fields": simplified_fields,
            "output_templates": result.get("output_templates", {}),
            "_meta": result.get("_meta", {})
        }

        if result.get("method") == "plain":
            response_data["_debug"] = {"system_prompt": result.get("full_system_prompt"), "query": params.get("query", "")}
        else:
            response_data["_debug"] = {
                "system_prompt": result.get("full_system_prompt"),
                "tools": [result.get("unified_function_schema")],
                "tool_choice": {"type": "function", "function": {"name": "fill_form"}},
                "query": params.get("query", "")
            }

        return Success(data=response_data)

    except ValueError as e:
        logger.error(f"LLM fill validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"LLM fill error: {e}")
        raise HTTPException(status_code=500, detail=f"LLM processing failed: {str(e)}")


# ==================== 分步 LLM 填单接口 ====================

@router.post(
    "/autofill/llm/fill/step",
    summary="分步LLM填单",
    response_model=StepLLMFillResponse,
)
async def step_llm_fill(
    request_data: StepLLMFillRequest,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """分步调用 LLM 填单，支持 session 管理和多轮数据存储

    - **session_id**: 会话ID，用于标识同一轮填单流程
    - **field_names**: 字段名称列表（可选，不传则返回所有字段）
    - **group_names**: 字段组名称列表（可选，不传则查询所有）
    - **system_prompt_group**: 用于获取system_prompt的字段组名（可选，不传则使用第一个group_name）
    - **query**: 用户输入的查询内容
    - **method**: LLM调用方法（可选）
    - **system_prompt**: 系统提示词（可选）
    - **include_reason**: 是否返回字段填写理由（可选，默认false）
    - **memory_rounds**: 保留历史消息的轮数（可选，默认0）
    - **is_last**: 是否为最后一次调用（可选，默认false）
    - **additional_data**: 附加数据（可选）
    - **use_additional_data**: 是否使用附加数据（可选，默认false）
    """
    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]
    session_id = request_data.session_id
    is_last = request_data.is_last

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    session_info = await step_llm_fill_service.get_session_info(session_id)
    current_step = session_info["call_count"] + 1

    logger.info(f"Step LLM fill: session_id={session_id}, step={current_step}, is_last={is_last}")

    try:
        # 调用 service 层方法（复用核心逻辑）
        result = await step_llm_fill_service.execute_llm_fill_step(
            tenant_id=tenant_id,
            app_name=app_name,
            session_id=session_id,
            field_names=request_data.field_names or [],
            group_names=request_data.group_names or [],
            system_prompt_group=request_data.system_prompt_group,
            query=request_data.query,
            is_last=is_last,
            method=request_data.method,
            system_prompt=request_data.system_prompt,
            additional_data=request_data.additional_data,
            use_additional_data=request_data.use_additional_data,
            include_reason=request_data.include_reason,
            memory_rounds=request_data.memory_rounds
        )

        # 组装响应数据
        # 简化字段结构，移除嵌套的 value 对象
        simplified_fields = _simplify_field_structure(result.get("result", {}))
        
        response_data = {
            "session_id": session_id,
            "step": current_step,
            "is_last": is_last,
            "status": "completed" if is_last else "processing",
            "app_name": app_name,
            "elapsed_time": result.get("elapsed_time", 0),
            "output_templates": result.get("output_templates", {}),
            "fields": simplified_fields
        }

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

    # 简化字段结构
    if result.get("merged_fields"):
        result["fields"] = _simplify_field_structure(result["merged_fields"])
        # 移除冗余的 merged_fields
        del result["merged_fields"]

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
        field_names=params.get("field_names", []),
        group_names=params.get("group_names", []),
        chat_record=params.get("chat_record", "")
    )

    return Success(data=result)
