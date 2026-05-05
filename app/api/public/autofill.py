"""
智能填单系统公开接口 (Dify/三方应用调用)
使用 API Key 认证，不依赖 JWT
"""
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request
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
from app.log import logger
from app.schemas.base import Success
from app.schemas.autofill import *
from app.services.autofill.ai_fill_service import get_ai_fill_service

autofill_public_router = APIRouter()


# ==================== 模板相关接口 ====================

async def list_summary_templates_handler(
    request: Request,
    auth_info: dict
):
    """
    查询模板列表处理逻辑
    """
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


# ==================== 下拉选项接口 ====================

async def list_dropdown_options_handler(
    request: Request,
    auth_info: dict
):
    """
    查询下拉选项列表处理逻辑
    支持扁平列表和树形结构两种返回格式
    """
    params = await parse_request_params(request, DropdownOptionListRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    q = Q(tenant_id=tenant_id, app_name=app_name)
    if params.get("class_name"):
        q &= Q(class_name=params["class_name"])

    parent_id = params.get("parent_id", 0)
    q &= Q(parent_id=parent_id)

    # 检查是否需要返回树形结构
    is_tree = params.get("tree", False)

    if is_tree:
        # 树形结构：递归返回所有子级
        async def build_tree(parent_id: int) -> list:
            children = await dropdown_option_controller.model.filter(
                tenant_id=tenant_id,
                app_name=app_name,
                parent_id=parent_id
            ).all()

            result = []
            for child in children:
                child_dict = {
                    "id": child.id,
                    "option_value": child.option_value,
                    "summary": child.summary,
                }
                # 递归获取子级
                sub_children = await build_tree(child.id)
                if sub_children:
                    child_dict["children"] = sub_children
                result.append(child_dict)
            return result

        tree_data = await build_tree(parent_id)
        return Success(data=tree_data)
    else:
        # 扁平结构：只返回直接子项
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

    参数说明:
        - class_name: 分类名称（可选）
        - parent_id: 父选项ID，0表示顶级（默认0）
        - tree: 是否返回树形结构（默认false）
            - false: 返回扁平列表，带has_children标记
            - true: 返回树形结构，递归包含所有子级

    示例:
        # 扁平结构（默认）
        GET /autofill/dropdown_options/list?class_name=400电话&parent_id=0
        # 返回: [{id, option_value, summary, has_children}, ...]

        # 树形结构
        GET /autofill/dropdown_options/list?class_name=400电话&parent_id=0&tree=true
        # 返回: [{id, option_value, summary, children: [...]}, ...]
    """
    return await list_dropdown_options_handler(request, auth_info)


async def get_dropdown_option_handler(
    request: Request,
    auth_info: dict
):
    """
    查询下拉选项详情处理逻辑
    """
    params = await parse_request_params(request, DropdownOptionDetailRequest)
    
    option = await dropdown_option_controller.model.filter(
        id=params["id"],
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"]
    ).first()

    if not option:
        raise HTTPException(status_code=404, detail="Option not found")

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


# ==================== 填单数据接口 ====================

async def record_fill_data_handler(
    request: Request,
    auth_info: dict
):
    """
    记录填单数据处理逻辑
    """
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


# ==================== AI 填单接口 ====================

async def get_ai_fill_data_handler(
    request: Request,
    auth_info: dict
):
    """
    获取AI填单数据处理逻辑
    支持同步(sync)和异步(async)两种模式
    """
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
        return Success(data=result)
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


async def get_ai_fill_data_result_handler(
    request: Request,
    auth_info: dict
):
    """
    查询AI填单异步处理结果
    """
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


# ==================== 字段组接口 ====================

async def get_field_group_handler(
    request: Request,
    auth_info: dict
):
    """
    查询字段组配置处理逻辑（改造后）
    - 支持通过 page_name + group_names 查询多个字段组
    - 支持通过 field_names 筛选指定字段
    - 返回组装后的Prompt、Function Calling Schema、字段明细等完整信息
    """
    from pydantic import BaseModel
    from app.services.autofill.prompt_service import build_function_schema, build_fields_instructions, assemble_prompt
    from app.models.autofill import FieldGroupFieldSpec

    class FieldGroupRequest(BaseModel):
        page_name: str = Field(..., description="页面名称（必填）")
        group_names: List[str] = Field(default_factory=list, description="字段组名称列表（可选，不传则查询所有）")
        field_names: List[str] = Field(default_factory=list, description="字段名称列表（可选，不传则返回所有字段）")

    params = await parse_request_params(request, FieldGroupRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 使用 page_name 查询页面
    page = await fill_page_controller.model.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        page_name=params.get("page_name")
    ).first()

    if not page:
        return Success(data=[])

    # 构建字段组查询条件
    q = Q(
        tenant_id=tenant_id,
        app_name=app_name,
        page_id=page.id
    )
    
    # 如果传了 group_names，则按名称筛选
    group_names = params.get("group_names", [])
    if group_names:
        q &= Q(group_name__in=group_names)

    field_groups = await field_group_config_controller.model.filter(q).all()

    # 获取字段名称筛选条件
    field_names_filter = set(params.get("field_names", []))

    # 构建完整返回数据
    result = []
    for fg in field_groups:
        # 获取字段明细
        relations = await FieldGroupFieldSpec.filter(
            field_group_id=fg.id,
            tenant_id=tenant_id,
            app_name=app_name
        ).all()
        field_spec_ids = [r.field_spec_id for r in relations]

        field_specs = []
        if field_spec_ids:
            # 构建字段查询条件
            field_q = Q(id__in=field_spec_ids, is_active=True)
            # 如果传了 field_names，则按名称筛选
            if field_names_filter:
                field_q &= Q(field_name__in=list(field_names_filter))
            
            field_specs = await field_spec_controller.model.filter(field_q).all()

        # 如果没有匹配的字段且传了 field_names 筛选，则跳过该字段组
        if field_names_filter and not field_specs:
            continue

        # 构建字段指令
        fields_instructions = build_fields_instructions(field_specs)

        # 构建Function Calling Schema
        function_schema = build_function_schema(fg, field_specs)

        # 组装示例Prompt
        example_query = "[用户对话内容将在这里插入]"
        assembled_prompt = assemble_prompt(fg, field_specs, example_query)

        result.append({
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
            # 新增字段
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

    return Success(data=result)


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


# ==================== 字段明细接口 ====================

async def list_field_spec_handler(
    request: Request,
    auth_info: dict
):
    """
    查询字段明细列表处理逻辑（改造后）
    - 支持通过 page_name + group_names 查询多个字段组
    - 支持通过 field_names 筛选指定字段
    """
    from pydantic import BaseModel
    from app.models.autofill import FieldGroupFieldSpec

    class FieldSpecListRequest(BaseModel):
        page_name: str = Field(..., description="页面名称（必填）")
        group_names: List[str] = Field(default_factory=list, description="字段组名称列表（可选，不传则查询所有）")
        field_names: List[str] = Field(default_factory=list, description="字段名称列表（可选，不传则返回所有字段）")

    params = await parse_request_params(request, FieldSpecListRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 1. 查找页面
    page = await fill_page_controller.model.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        page_name=params.get("page_name")
    ).first()

    if not page:
        return Success(data=[])

    # 2. 查找字段组（支持多个）
    group_q = Q(
        tenant_id=tenant_id,
        app_name=app_name,
        page_id=page.id
    )
    
    group_names = params.get("group_names", [])
    if group_names:
        group_q &= Q(group_name__in=group_names)
    
    field_groups = await field_group_config_controller.model.filter(group_q).all()

    if not field_groups:
        return Success(data=[])

    # 3. 收集所有字段组关联的字段ID
    field_group_ids = [fg.id for fg in field_groups]
    relations = await FieldGroupFieldSpec.filter(
        field_group_id__in=field_group_ids,
        tenant_id=tenant_id,
        app_name=app_name
    ).all()

    field_spec_ids = list(set([r.field_spec_id for r in relations]))

    if not field_spec_ids:
        return Success(data=[])

    # 4. 构建字段查询条件
    q = Q(id__in=field_spec_ids, is_active=True)

    # 如果传入了 field_names，按名称筛选
    field_names = params.get("field_names", [])
    if field_names:
        q &= Q(field_name__in=field_names)

    field_specs = await field_spec_controller.model.filter(q).all()

    # 5. 获取每个字段关联的字段组
    result = []
    for fs in field_specs:
        relations = await FieldGroupFieldSpec.filter(field_spec_id=fs.id).all()
        group_ids = [r.field_group_id for r in relations]
        result.append({
            "id": fs.id,
            "field_name": fs.field_name,
            "field_label": fs.field_label,
            "field_type": fs.field_type,
            "fill_instruction": fs.fill_instruction,
            "options": fs.options,
            "corrections": fs.corrections,
            "is_active": fs.is_active,
            "field_group_ids": group_ids,
        })

    return Success(data=result)


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


# ==================== 合并查询接口 ====================

async def get_field_groups_schema_handler(
    request: Request,
    auth_info: dict
):
    """
    合并查询接口：查询多个字段组的完整Schema信息
    - 支持通过 page_name + group_names 查询多个字段组
    - 支持通过 field_names 筛选指定字段
    - 返回组装后的Prompt、Function Calling Schema等完整信息
    
    使用场景：
    1. 传了 group_names，未传 field_names -> 返回这些字段组下所有字段的完整信息
    2. 传了 group_names + field_names -> 仅返回指定字段的完整信息（字段必须在指定字段组中）
    3. 未传 group_names，传了 field_names -> 返回包含这些字段的所有字段组的完整信息
    """
    from pydantic import BaseModel
    from app.services.autofill.prompt_service import build_function_schema, build_fields_instructions, assemble_prompt
    from app.models.autofill import FieldGroupFieldSpec

    class FieldGroupsSchemaRequest(BaseModel):
        page_name: str = Field(..., description="页面名称（必填）")
        group_names: List[str] = Field(default_factory=list, description="字段组名称列表（可选）")
        field_names: List[str] = Field(default_factory=list, description="字段名称列表（可选）")

    params = await parse_request_params(request, FieldGroupsSchemaRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 1. 查找页面
    page = await fill_page_controller.model.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        page_name=params.get("page_name")
    ).first()

    if not page:
        return Success(data={"field_groups": [], "fields": [], "combined_schema": None})

    field_names_filter = set(params.get("field_names", []))
    group_names_filter = set(params.get("group_names", []))

    # 2. 确定要查询的字段组
    if group_names_filter:
        # 如果传了 group_names，查询指定字段组
        field_groups = await field_group_config_controller.model.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            page_id=page.id,
            group_name__in=list(group_names_filter)
        ).all()
    else:
        # 如果没传 group_names，但有 field_names，需要找出包含这些字段的字段组
        if field_names_filter:
            # 先找出这些字段
            field_specs = await field_spec_controller.model.filter(
                tenant_id=tenant_id,
                app_name=app_name,
                field_name__in=list(field_names_filter),
                is_active=True
            ).all()
            field_spec_ids = [fs.id for fs in field_specs]
            
            # 找出包含这些字段的字段组ID
            relations = await FieldGroupFieldSpec.filter(
                field_spec_id__in=field_spec_ids,
                tenant_id=tenant_id,
                app_name=app_name
            ).all()
            field_group_ids = list(set([r.field_group_id for r in relations]))
            
            # 查询这些字段组
            field_groups = await field_group_config_controller.model.filter(
                id__in=field_group_ids,
                tenant_id=tenant_id,
                app_name=app_name,
                page_id=page.id
            ).all()
        else:
            # 什么都没传，返回空
            return Success(data={"field_groups": [], "fields": [], "combined_schema": None})

    if not field_groups:
        return Success(data={"field_groups": [], "fields": [], "combined_schema": None})

    # 3. 构建返回数据
    result_groups = []
    all_field_specs = []
    all_field_ids = set()

    for fg in field_groups:
        # 获取字段组关联的字段
        relations = await FieldGroupFieldSpec.filter(
            field_group_id=fg.id,
            tenant_id=tenant_id,
            app_name=app_name
        ).all()
        field_spec_ids = [r.field_spec_id for r in relations]

        # 构建字段查询条件
        field_q = Q(id__in=field_spec_ids, is_active=True)
        if field_names_filter:
            field_q &= Q(field_name__in=list(field_names_filter))

        field_specs = await field_spec_controller.model.filter(field_q).all()

        # 如果传了 field_names 筛选但没有匹配字段，跳过该字段组
        if field_names_filter and not field_specs:
            continue

        # 收集所有字段（去重）
        for fs in field_specs:
            if fs.id not in all_field_ids:
                all_field_ids.add(fs.id)
                all_field_specs.append(fs)

        # 构建字段指令
        fields_instructions = build_fields_instructions(field_specs)

        # 构建Function Calling Schema
        function_schema = build_function_schema(fg, field_specs)

        # 组装示例Prompt
        example_query = "[用户对话内容将在这里插入]"
        assembled_prompt = assemble_prompt(fg, field_specs, example_query)

        result_groups.append({
            "id": fg.id,
            "group_name": fg.group_name,
            "group_code": fg.group_code,
            "page_id": fg.page_id,
            "page_name": page.page_name,
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

    # 4. 构建合并后的Schema（所有字段的汇总）
    combined_schema = None
    if all_field_specs:
        # 使用第一个字段组的模板作为基础
        base_fg = field_groups[0] if field_groups else None
        if base_fg:
            combined_instructions = build_fields_instructions(all_field_specs)
            
            # 构建符合 OpenAI 规范的 Function Schema
            combined_function_schema = {
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
            
            # 合并所有字段的参数
            for fs in all_field_specs:
                param_info = _build_field_param(fs)
                combined_function_schema["function"]["parameters"]["properties"][fs.field_name] = param_info
                # 默认所有字段都是 required
                combined_function_schema["function"]["parameters"]["required"].append(fs.field_name)

            combined_prompt = assemble_prompt(base_fg, all_field_specs, "[用户对话内容将在这里插入]")
            
            # 如果 template_base 为空，使用默认模板
            template_base = base_fg.prompt_template_base or """你是一个智能填单助手。请根据以下对话内容，提取指定字段的信息。

需要提取的字段：
{{fields_instructions}}

对话内容：
{{query}}

请严格按照字段要求提取信息，并以JSON格式返回结果。"""
            
            combined_schema = {
                "prompt_info": {
                    "template_base": template_base,
                    "fields_instructions": combined_instructions,
                    "assembled_prompt": combined_prompt,
                },
                "function_calling": {
                    "schema": combined_function_schema,
                    "json_schema": json.dumps(combined_function_schema, ensure_ascii=False, indent=2),
                },
            }

    return Success(data={
        "field_groups": result_groups,
        "fields_summary": {
            "total_fields": len(all_field_specs),
            "field_names": [fs.field_name for fs in all_field_specs],
        },
        "combined_schema": combined_schema,
    })


def _build_field_param(field_spec):
    """构建单个字段的参数定义（符合 OpenAI Function Calling 规范）"""
    # 构建描述：优先使用 fill_instruction，其次是 field_label
    description = field_spec.fill_instruction or field_spec.field_label or field_spec.field_name
    
    param = {
        "type": "string",
        "description": description,
    }
    
    # 如果有选项，添加 enum（使用 label 便于 LLM 理解）
    if field_spec.options and field_spec.options.get("items"):
        items = field_spec.options.get("items", [])
        # 过滤已删除的选项，使用 label 作为 enum 值
        valid_items = [item for item in items if not item.get("is_deleted", False)]
        if valid_items:
            # 使用 label 作为 enum 值（LLM 更容易理解）
            param["enum"] = [item.get("label") for item in valid_items if item.get("label")]
            
            # 在 description 中追加选项说明
            option_descs = []
            for item in valid_items[:10]:  # 最多显示前10个选项，避免 description 过长
                label = item.get("label", "")
                fill_inst = item.get("fill_instruction", "")
                if fill_inst:
                    option_descs.append(f"{label}: {fill_inst}")
                else:
                    option_descs.append(label)
            
            if option_descs:
                param["description"] = f"{description}。可选值：{', '.join(option_descs)}"
                if len(valid_items) > 10:
                    param["description"] += f" 等共{len(valid_items)}个选项"
    
    return param


@autofill_public_router.get("/autofill/field_groups/schema", summary="查询多个字段组的完整Schema")
@autofill_public_router.post("/autofill/field_groups/schema", summary="查询多个字段组的完整Schema")
async def get_field_groups_schema(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    查询多个字段组的完整Schema信息（合并接口）
    支持 GET 和 POST 方法
    支持参数传递方式: Query / Form-Data / JSON Body
    
    请求参数:
        - page_name: 页面名称（必填）
        - group_names: 字段组名称列表（可选）
        - field_names: 字段名称列表（可选）
    
    使用场景:
        1. 只传 group_names: 返回这些字段组下所有字段的完整信息
        2. 传 group_names + field_names: 仅返回指定字段的完整信息
        3. 只传 field_names: 返回包含这些字段的所有字段组信息
    
    返回:
        - field_groups: 字段组列表（每个包含Prompt、Function Schema等）
        - fields_summary: 字段汇总信息
        - combined_schema: 合并后的Schema（所有字段汇总）
    """
    return await get_field_groups_schema_handler(request, auth_info)


# ==================== LLM 填单接口 ====================

async def llm_fill_handler(
    request: Request,
    auth_info: dict
):
    """
    直接LLM填单处理逻辑
    """
    from pydantic import BaseModel, Field

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

    from app.services.autofill.prompt_service import build_function_schema
    from app.services.llm.llm_proxy_service import llm_proxy_service
    from app.controllers.llm_config import llm_config_controller

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


# ==================== 下拉选项层级接口 ====================

async def list_first_level_menus_handler(
    request: Request,
    auth_info: dict
):
    """
    A1. 获取所有一级菜单
    根据 tenant_id + app_name + class_name 查询所有 parent_id=0 的选项
    """
    from pydantic import BaseModel

    class FirstLevelMenusRequest(BaseModel):
        class_name: str = Field("", description="分类名称")

    params = await parse_request_params(request, FirstLevelMenusRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    q = Q(tenant_id=tenant_id, app_name=app_name, parent_id=0)
    if params.get("class_name"):
        q &= Q(class_name=params["class_name"])

    options = await dropdown_option_controller.model.filter(q).all()

    return Success(data=[
        {
            "id": o.id,
            "option_value": o.option_value,
            "summary": o.summary,
            "class_name": o.class_name,
        }
        for o in options
    ])


@autofill_public_router.get("/autofill/dropdown/first_level", summary="A1. 获取所有一级菜单")
@autofill_public_router.post("/autofill/dropdown/first_level", summary="A1. 获取所有一级菜单")
async def list_first_level_menus(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    获取所有一级菜单（parent_id=0 的选项）
    支持 GET 和 POST 方法
    支持参数传递方式: Query / Form-Data / JSON Body
    可选参数: class_name（分类名称）
    """
    return await list_first_level_menus_handler(request, auth_info)


async def get_submenus_tree_handler(
    request: Request,
    auth_info: dict
):
    """
    A2. 根据一级菜单名称+应用名称+分类获取二三级菜单（树形结构）
    """
    from pydantic import BaseModel

    class SubmenusTreeRequest(BaseModel):
        first_level_value: str = Field(..., description="一级菜单选项值")
        class_name: str = Field("", description="分类名称")

    params = await parse_request_params(request, SubmenusTreeRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]
    first_level_value = params.get("first_level_value")
    class_name = params.get("class_name", "")

    if not first_level_value:
        raise HTTPException(status_code=400, detail="first_level_value is required")

    # 查找一级菜单
    q = Q(
        tenant_id=tenant_id,
        app_name=app_name,
        parent_id=0,
        option_value=first_level_value
    )
    if class_name:
        q &= Q(class_name=class_name)

    first_level = await dropdown_option_controller.model.filter(q).first()

    if not first_level:
        raise HTTPException(status_code=404, detail="First level menu not found")

    # 递归获取树形结构
    async def build_tree(parent_id: int) -> list:
        children = await dropdown_option_controller.model.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            parent_id=parent_id
        ).all()

        result = []
        for child in children:
            child_dict = {
                "id": child.id,
                "option_value": child.option_value,
                "summary": child.summary,
            }
            # 递归获取子级
            sub_children = await build_tree(child.id)
            if sub_children:
                child_dict["children"] = sub_children
            result.append(child_dict)
        return result

    tree_data = await build_tree(first_level.id)

    return Success(data={
        "first_level": {
            "id": first_level.id,
            "option_value": first_level.option_value,
            "summary": first_level.summary,
            "class_name": first_level.class_name,
        },
        "children": tree_data
    })


@autofill_public_router.get("/autofill/dropdown/submenus_tree", summary="A2. 获取二三级菜单树形结构")
@autofill_public_router.post("/autofill/dropdown/submenus_tree", summary="A2. 获取二三级菜单树形结构")
async def get_submenus_tree(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    根据一级菜单名称+应用名称+分类获取二三级菜单（树形结构）
    支持 GET 和 POST 方法
    支持参数传递方式: Query / Form-Data / JSON Body
    必需参数: first_level_value（一级菜单选项值）
    可选参数: class_name（分类名称）
    """
    return await get_submenus_tree_handler(request, auth_info)


# ==================== 字段组批量创建/更新接口 ====================

async def upsert_field_group_handler(
    request: Request,
    auth_info: dict
):
    """
    创建或更新字段组，并批量处理字段列表
    - 如果字段组不存在，自动创建
    - 如果页面不存在，返回错误
    - 遍历字段列表：字段不存在则创建并添加关联，存在则只添加关联关系
    """
    from pydantic import BaseModel
    from app.models.autofill import FieldGroupFieldSpec, generate_field_group_code
    from app.schemas.fill_page import FieldGroupConfigCreate, OutputTemplateItem, FieldSpecCreate, FieldSpecUpdate, FieldOptions

    class FieldItem(BaseModel):
        field_name: str
        field_label: Optional[str] = None
        field_type: str = "text"
        fill_instruction: Optional[str] = None
        options: Optional[Dict] = None

    class UpsertFieldGroupRequest(BaseModel):
        page_name: str
        group_name: str
        group_code: Optional[str] = None
        output_templates: Optional[Dict] = None
        prompt_template_base: Optional[str] = None
        fields: List[FieldItem] = []

    params = await parse_request_params(request, UpsertFieldGroupRequest)
    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 1. 查找页面
    page = await fill_page_controller.model.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        page_name=params["page_name"]
    ).first()

    if not page:
        raise HTTPException(status_code=404, detail=f"Page '{params['page_name']}' not found")

    # 2. 查找或创建字段组
    field_group = await field_group_config_controller.model.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        page_id=page.id,
        group_name=params["group_name"]
    ).first()

    if field_group:
        # 更新字段组
        update_data = {}
        if params.get("output_templates") is not None:
            update_data["output_templates"] = params["output_templates"]
        if params.get("prompt_template_base") is not None:
            update_data["prompt_template_base"] = params["prompt_template_base"]
        if update_data:
            update_data["version"] = field_group.version + 1
            await field_group_config_controller.update(id=field_group.id, obj_in=update_data)
            field_group = await field_group_config_controller.get(id=field_group.id)
    else:
        # 创建字段组
        group_code = params.get("group_code") or generate_field_group_code()
        output_templates = params.get("output_templates") or {}

        # 转换output_templates格式
        formatted_templates = {}
        for key, value in output_templates.items():
            if isinstance(value, dict):
                formatted_templates[key] = OutputTemplateItem(**value)
            else:
                formatted_templates[key] = OutputTemplateItem(template=value, description="")

        create_data = FieldGroupConfigCreate(
            group_name=params["group_name"],
            group_code=group_code,
            page_id=page.id,
            page_name=page.page_name,
            app_name=app_name,
            tenant_id=tenant_id,
            output_templates=formatted_templates,
            prompt_template_base=params.get("prompt_template_base") or ""
        )
        field_group = await field_group_config_controller.create_field_group(obj_in=create_data)

    # 3. 批量处理字段列表
    processed_fields = []
    fields = params.get("fields", [])

    for field_item in fields:
        field_name = field_item["field_name"]
        field_label = field_item.get("field_label") or field_name
        field_type = field_item.get("field_type", "text")
        fill_instruction = field_item.get("fill_instruction") or ""
        options = field_item.get("options", {})

        # 验证field_type
        if field_type not in ["select", "text"]:
            field_type = "text"

        # 查找或创建字段
        field_spec = await field_spec_controller.model.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            field_name=field_name
        ).first()

        is_new_relation = False

        if field_spec:
            # 字段已存在，更新信息
            # 先获取字段当前关联的所有字段组ID
            existing_relations = await FieldGroupFieldSpec.filter(field_spec_id=field_spec.id).all()
            existing_group_ids = [r.field_group_id for r in existing_relations]
            
            # 确保包含当前字段组ID
            if field_group.id not in existing_group_ids:
                existing_group_ids.append(field_group.id)
            
            update_data = FieldSpecUpdate(
                id=field_spec.id,
                field_label=field_label,
                field_type=field_type,
                fill_instruction=fill_instruction,
                field_group_ids=existing_group_ids
            )

            # 处理options
            if options:
                if isinstance(options, dict):
                    update_data.options = FieldOptions(**options)
                else:
                    update_data.options = options

            field_spec = await field_spec_controller.update_field_spec(
                id=field_spec.id,
                obj_in=update_data,
                tenant_id=tenant_id,
                app_name=app_name
            )
        else:
            # 字段不存在，创建新字段
            create_data = FieldSpecCreate(
                field_name=field_name,
                field_label=field_label,
                field_type=field_type,
                fill_instruction=fill_instruction,
                field_group_ids=[field_group.id]
            )

            # 处理options
            if options:
                if isinstance(options, dict):
                    create_data.options = FieldOptions(**options)
                else:
                    create_data.options = options

            field_spec = await field_spec_controller.create_field_spec(
                obj_in=create_data,
                tenant_id=tenant_id,
                app_name=app_name
            )
            is_new_relation = True

        # 确保字段与当前字段组的关联关系
        existing_relation = await FieldGroupFieldSpec.filter(
            field_group_id=field_group.id,
            field_spec_id=field_spec.id
        ).first()

        if not existing_relation:
            await FieldGroupFieldSpec.create(
                field_group_id=field_group.id,
                field_spec_id=field_spec.id,
                tenant_id=tenant_id,
                app_name=app_name
            )
            is_new_relation = True

        # 获取字段关联的所有字段组
        relations = await FieldGroupFieldSpec.filter(field_spec_id=field_spec.id).all()
        group_ids = [r.field_group_id for r in relations]

        processed_fields.append({
            "id": field_spec.id,
            "field_name": field_spec.field_name,
            "field_label": field_spec.field_label,
            "field_type": field_spec.field_type,
            "field_group_ids": group_ids,
            "is_new_relation": is_new_relation
        })

    return Success(data={
        "id": field_group.id,
        "group_name": field_group.group_name,
        "group_code": field_group.group_code,
        "page_id": field_group.page_id,
        "page_name": page.page_name,
        "output_templates": field_group.output_templates,
        "version": field_group.version,
        "fields": processed_fields,
        "field_count": len(processed_fields)
    })


@autofill_public_router.post("/autofill/field_group/upsert", summary="创建或更新字段组（含批量字段）")
async def upsert_field_group(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    创建或更新字段组，并批量处理字段列表
    支持字段组不存在时自动创建
    支持字段不存在时自动创建，存在时更新并确保关联关系
    只支持 POST 方法
    支持参数传递方式: JSON Body
    """
    return await upsert_field_group_handler(request, auth_info)


# ==================== 字段明细管理公共接口 ====================

async def create_field_spec_public_handler(
    request: Request,
    auth_info: dict
):
    """
    公共接口：创建字段明细
    """
    from pydantic import BaseModel, Field

    class FieldSpecCreateRequest(BaseModel):
        field_group_id: int = Field(..., description="字段组ID")
        field_name: str = Field(..., description="字段名（英文）")
        field_label: str = Field(..., description="字段显示名称")
        field_type: str = Field(default="select", description="字段类型: select/text")
        fill_instruction: str = Field(default="", description="字段填写指引")
        options: Dict = Field(default_factory=dict, description="选项配置")

    params = await parse_request_params(request, FieldSpecCreateRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 验证字段组是否存在
    field_group = await field_group_config_controller.model.filter(
        id=params["field_group_id"],
        tenant_id=tenant_id,
        app_name=app_name
    ).first()

    if not field_group:
        raise HTTPException(status_code=404, detail="Field group not found")

    # 检查同一字段组下字段名是否已存在
    existing = await field_spec_controller.model.filter(
        field_group_id=params["field_group_id"],
        field_name=params["field_name"]
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Field name already exists in this group")

    # 创建字段
    field_data = {
        "field_group_id": params["field_group_id"],
        "field_name": params["field_name"],
        "field_label": params["field_label"],
        "field_type": params.get("field_type", "select"),
        "fill_instruction": params.get("fill_instruction", ""),
        "options": params.get("options", {}),
        "corrections": [],
        "is_active": True,
        "tenant_id": tenant_id,
    }

    spec = await field_spec_controller.create(obj_in=field_data)

    return Success(data={
        "id": spec.id,
        "field_name": spec.field_name,
        "field_label": spec.field_label,
        "field_type": spec.field_type,
    })


@autofill_public_router.post("/autofill/field_spec/create", summary="公共接口：创建字段明细")
async def create_field_spec_public(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    公共接口：创建字段明细
    只支持 POST 方法
    支持参数传递方式: JSON Body
    必需参数: field_group_id, field_name, field_label
    """
    return await create_field_spec_public_handler(request, auth_info)
