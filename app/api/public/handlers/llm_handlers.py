"""
LLM/AI 填单相关接口
"""
import json
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
from app.models.autofill import FieldGroupFieldSpec, FillPage
from app.schemas.autofill import AIFillDataRequest, AIFillDataResultRequest
from app.schemas.base import Success
from app.services.autofill.ai_fill_service import get_ai_fill_service
from app.services.autofill.prompt_service import (
    assemble_prompt,
    build_fields_instructions,
    build_function_schema,
)
from app.services.llm.llm_proxy_service import llm_proxy_service
from app.services.llm.structured_output import StructuredOutputService
from app.api.public.handlers.field_group_handlers import fetch_field_groups

router = APIRouter()


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
    from app.schemas.public.field_group import LLMFillRequest

    params = await parse_request_params(request, LLMFillRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 处理 group_fields 参数（新的传参格式）
    group_fields = params.get("group_fields")
    if group_fields:
        # 使用新的传参格式：group_fields = {"default": ["field1", "field2"], "group2": []}
        group_names = list(group_fields.keys())
        # 收集所有指定的字段名（用于过滤）
        all_field_names = []
        for fields in group_fields.values():
            if fields:  # 如果不是空列表，则添加这些字段
                all_field_names.extend(fields)
        field_names = all_field_names if all_field_names else []
    else:
        # 使用旧的传参格式
        group_names = params.get("group_names", [])
        field_names = params.get("field_names", [])

    # 调用 fetch_field_groups 获取字段组配置（返回可直接使用的统一 schema）
    result_data = await fetch_field_groups(
        tenant_id=tenant_id,
        app_name=app_name,
        page_name=params.get("page_name"),
        group_names=group_names,
        field_names=field_names,
        group_fields=group_fields  # 传递 group_fields 以支持按字段组分别过滤
    )

    unified_function_schema = result_data.get("unified_function_schema")
    if not unified_function_schema:
        raise HTTPException(status_code=404, detail="No field groups found")

    query = params.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    config = await llm_config_controller.get_default_config(
        tenant_id=tenant_id,
        app_name=app_name
    )

    if not config:
        raise HTTPException(status_code=500, detail="No LLM configuration found")

    # 构建包含字段指引的 system_prompt
    base_prompt = result_data.get("combined_prompt", "你是一个智能填单助手。")

    # 从数据库查询字段模型对象用于构建指引
    field_names = params.get("field_names", [])
    if field_names:
        field_specs = await field_spec_controller.model.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            field_name__in=field_names,
            is_active=True
        ).all()
    else:
        field_specs = []

    # 添加字段指引到 system_prompt
    if field_specs:
        fields_instructions = build_fields_instructions(field_specs)
        system_prompt = f"""{base_prompt}

请根据以下字段指引从对话中提取信息：

{fields_instructions}

请严格按照字段要求提取信息。"""
    else:
        system_prompt = base_prompt

    try:
        llm_result = await llm_proxy_service.process_request(
            query=query,
            tools=[unified_function_schema],
            system_prompt=system_prompt,
            tool_choice={"type": "function", "function": {"name": "fill_form"}},
            config=config
        )

        extracted_data = {k: v for k, v in llm_result.items() if not k.startswith('_')}

        # 调试信息：打印给大模型的参数
        debug_info = {
            "system_prompt": system_prompt,
            "tools": [unified_function_schema],
            "tool_choice": {"type": "function", "function": {"name": "fill_form"}},
            "query": query
        }

        return Success(data={
            "page_name": params.get("page_name"),
            "group_names": params.get("group_names", []),
            "result": extracted_data,
            "_meta": llm_result.get("_meta", {}),
            "_debug": debug_info
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


async def optimize_field_instructions_handler(request: Request, auth_info: dict):
    """优化字段填写指引处理逻辑"""
    from app.schemas.public.field_group import OptimizeFieldInstructionRequest

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
            "options": field.options.get("items", []) if field.options and field_type == "select" else []
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
