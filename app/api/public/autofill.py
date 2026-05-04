"""
智能填单系统公开接口 (Dify/三方应用调用)
使用 API Key 认证，不依赖 JWT
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, Request
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
from app.schemas.base import Fail, Success
from app.schemas.autofill import *
from app.services.autofill.ai_fill_service import get_ai_fill_service
from app.settings.config import settings

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
    """
    params = await parse_request_params(request, DropdownOptionListRequest)
    
    q = Q(tenant_id=auth_info["tenant_id"], app_name=auth_info["app_name"])
    if params.get("class_name"):
        q &= Q(class_name=params["class_name"])

    parent_id = params.get("parent_id", 0)
    q &= Q(parent_id=parent_id)

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
    - 支持通过 page_name + group_name 查询
    """
    from pydantic import BaseModel

    class FieldGroupRequest(BaseModel):
        page_name: str = Field(..., description="页面名称（必填）")
        group_name: str = Field(..., description="字段组名称（必填）")

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
        page_id=page.id,
        group_name=params.get("group_name")
    )

    field_groups = await field_group_config_controller.model.filter(q).all()

    return Success(data=[
        {
            "id": fg.id,
            "group_name": fg.group_name,
            "group_code": fg.group_code,
            "page_id": fg.page_id,
            "page_name": page.page_name if page else "",
            "prompt_template_base": fg.prompt_template_base,
            "output_templates": fg.output_templates,
            "version": fg.version,
        }
        for fg in field_groups
    ])


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
    - 支持通过 page_name + group_name + field_name 查询
    """
    from pydantic import BaseModel
    from app.models.autofill import FieldGroupFieldSpec

    class FieldSpecListRequest(BaseModel):
        page_name: str = Field(..., description="页面名称（必填）")
        group_name: str = Field(..., description="字段组名称（必填）")
        field_name: Optional[str] = Field(None, description="字段名（可选，精确匹配）")

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

    # 2. 查找字段组
    field_group = await field_group_config_controller.model.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        page_id=page.id,
        group_name=params.get("group_name")
    ).first()

    if not field_group:
        return Success(data=[])

    # 3. 通过中间表查询关联的字段ID
    relations = await FieldGroupFieldSpec.filter(
        field_group_id=field_group.id,
        tenant_id=tenant_id,
        app_name=app_name
    ).all()

    field_spec_ids = [r.field_spec_id for r in relations]

    if not field_spec_ids:
        return Success(data=[])

    # 4. 构建字段查询条件
    q = Q(id__in=field_spec_ids, is_active=True)

    # 如果传入了 field_name，精确匹配
    if params.get("field_name"):
        q &= Q(field_name=params["field_name"])

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
