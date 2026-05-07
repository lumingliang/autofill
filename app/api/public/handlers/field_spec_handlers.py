"""
字段明细相关接口
全部采用POST路由，请求参数使用schema定义
"""
from typing import List, Optional

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
from app.models.autofill import FieldGroupFieldSpec, generate_field_group_code
from app.schemas.base import Success
from app.schemas.fill_page import FieldSpecCreate, FieldSpecUpdate, FieldOptions, OutputTemplateItem
from app.schemas.public import (
    FieldSpecListRequest,
    FieldSpecCreateRequest,
    UpsertFieldGroupRequest,
)

router = APIRouter()


async def list_field_spec_handler(request: Request, auth_info: dict):
    """
    查询字段明细列表处理逻辑
    - 支持通过 page_name + group_names 查询多个字段组
    - 支持通过 field_names 筛选指定字段
    """
    params = await parse_request_params(request, FieldSpecListRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    page = await fill_page_controller.model.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        page_name=params.get("page_name")
    ).first()

    if not page:
        return Success(data=[])

    group_q = Q(tenant_id=tenant_id, app_name=app_name, page_id=page.id)
    group_names = params.get("group_names", [])
    if group_names:
        group_q &= Q(group_name__in=group_names)

    field_groups = await field_group_config_controller.model.filter(group_q).all()
    if not field_groups:
        return Success(data=[])

    field_group_ids = [fg.id for fg in field_groups]
    relations = await FieldGroupFieldSpec.filter(
        field_group_id__in=field_group_ids,
        tenant_id=tenant_id,
        app_name=app_name
    ).all()

    field_spec_ids = list(set([r.field_spec_id for r in relations]))
    if not field_spec_ids:
        return Success(data=[])

    q = Q(id__in=field_spec_ids, is_active=True)
    field_names = params.get("field_names", [])
    if field_names:
        q &= Q(field_name__in=field_names)

    field_specs = await field_spec_controller.model.filter(q).all()

    result = []
    for fs in field_specs:
        relations = await FieldGroupFieldSpec.filter(field_spec_id=fs.id).all()
        group_ids = [r.field_group_id for r in relations]

        groups = await field_group_config_controller.model.filter(id__in=group_ids).all()
        group_info = [{"id": g.id, "group_name": g.group_name, "group_code": g.group_code} for g in groups]

        result.append({
            "id": fs.id,
            "field_name": fs.field_name,
            "field_label": fs.field_label,
            "field_type": fs.field_type,
            "fill_instruction": fs.fill_instruction,
            "options": fs.options,
            "corrections": fs.corrections,
            "is_active": fs.is_active,
            "field_groups": group_info
        })

    return Success(data=result)


@router.post("/autofill/field_spec/list", summary="查询字段明细列表")
async def list_field_spec(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    根据app_name/page_name/group_names查询字段明细列表
    只支持 POST 方法
    支持参数传递方式: JSON Body
    """
    return await list_field_spec_handler(request, auth_info)


async def create_field_spec_public_handler(request: Request, auth_info: dict):
    """公共接口：创建字段明细"""
    params = await parse_request_params(request, FieldSpecCreateRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    field_group = await field_group_config_controller.model.filter(
        id=params["field_group_id"],
        tenant_id=tenant_id,
        app_name=app_name
    ).first()

    if not field_group:
        raise HTTPException(status_code=404, detail="Field group not found")

    existing = await field_spec_controller.model.filter(
        field_group_id=params["field_group_id"],
        field_name=params["field_name"]
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Field name already exists in this group")

    field_data = {
        "field_group_id": params["field_group_id"],
        "field_name": params["field_name"],
        "field_label": params["field_label"],
        "field_type": params.get("field_type", "text"),
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


@router.post("/autofill/field_spec/create", summary="公共接口：创建字段明细")
async def create_field_spec_public(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    公共接口：创建字段明细
    只支持 POST 方法
    支持参数传递方式: JSON Body
    """
    return await create_field_spec_public_handler(request, auth_info)


async def upsert_field_group_handler(request: Request, auth_info: dict):
    """
    创建或更新字段组，并批量处理字段列表
    - 如果字段组不存在，自动创建
    - 如果页面不存在，返回错误
    - 遍历字段列表：字段不存在则创建并添加关联，存在则只添加关联关系
    """
    params = await parse_request_params(request, UpsertFieldGroupRequest)
    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    page = await fill_page_controller.model.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        page_name=params["page_name"]
    ).first()

    if not page:
        raise HTTPException(status_code=404, detail=f"Page '{params['page_name']}' not found")

    field_group = await field_group_config_controller.model.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        page_id=page.id,
        group_name=params["group_name"]
    ).first()

    if field_group:
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
        group_code = params.get("group_code") or generate_field_group_code()
        output_templates = params.get("output_templates") or {}

        formatted_templates = {}
        for key, value in output_templates.items():
            if isinstance(value, dict):
                formatted_templates[key] = OutputTemplateItem(**value)
            else:
                formatted_templates[key] = OutputTemplateItem(template=value, description="")

        from app.schemas.fill_page import FieldGroupConfigCreate
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

    processed_fields = []
    fields = params.get("fields", [])

    for field_item in fields:
        field_name = field_item["field_name"]
        field_label = field_item.get("field_label") or field_name
        field_type = field_item.get("field_type", "text")
        fill_instruction = field_item.get("fill_instruction") or ""
        options = field_item.get("options", {})

        # 支持 "select" 作为下拉类型的别名，根据 selection_mode 判断单选/多选
        if field_type == "select":
            # 从 options 中获取 selection_mode，0=单选，1=多选
            selection_mode = options.get("selection_mode", 1)
            field_type = "select_single" if selection_mode == 0 else "select_multi"
        if field_type not in ["text", "select_single", "select_multi"]:
            field_type = "text"

        field_spec = await field_spec_controller.model.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            field_name=field_name
        ).first()

        is_new_relation = False

        if field_spec:
            existing_relations = await FieldGroupFieldSpec.filter(field_spec_id=field_spec.id).all()
            existing_group_ids = [r.field_group_id for r in existing_relations]
            if field_group.id not in existing_group_ids:
                existing_group_ids.append(field_group.id)

            update_data = FieldSpecUpdate(
                id=field_spec.id,
                field_label=field_label,
                field_type=field_type,
                fill_instruction=fill_instruction,
                field_group_ids=existing_group_ids
            )

            if options:
                # 处理 is_append 逻辑：合并新旧 options
                is_append = params.get("is_append", False)
                if is_append and field_spec.options:
                    # 合并新旧 options
                    existing_items = field_spec.options.items if field_spec.options else []
                    new_items = options.get("items", []) if isinstance(options, dict) else []

                    # 使用 label 作为 key 去重，新值覆盖旧值
                    merged_items_map = {item["label"]: item for item in existing_items}
                    for new_item in new_items:
                        if isinstance(new_item, dict) and "label" in new_item:
                            merged_items_map[new_item["label"]] = new_item

                    merged_items = list(merged_items_map.values())
                    # 如果 options 中没有设置 source，默认设置为 static
                    source = "static"
                    if isinstance(options, dict) and options.get("source"):
                        source = options["source"]

                    # 合并数量限制配置（新值覆盖旧值，仅多选时有效）
                    min_selections = options.get("min_selections") if isinstance(options, dict) else None
                    max_selections = options.get("max_selections") if isinstance(options, dict) else None

                    # 如果没有传新值，保留旧值
                    old_options = field_spec.options or {}
                    if min_selections is None and hasattr(old_options, 'min_selections'):
                        min_selections = old_options.min_selections
                    if max_selections is None and hasattr(old_options, 'max_selections'):
                        max_selections = old_options.max_selections

                    merged_options = {
                        "items": merged_items,
                        "source": source,
                        "min_selections": min_selections if min_selections is not None else 1,
                        "max_selections": max_selections if max_selections is not None else 0
                    }
                    update_data.options = FieldOptions(**merged_options)
                else:
                    # 直接覆盖
                    if isinstance(options, dict):
                        # 如果 options 中没有设置 source，默认设置为 static
                        if not options.get("source"):
                            options["source"] = "static"
                        # 设置数量限制默认值
                        if "min_selections" not in options:
                            options["min_selections"] = 1
                        if "max_selections" not in options:
                            options["max_selections"] = 0
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
            create_data = FieldSpecCreate(
                field_name=field_name,
                field_label=field_label,
                field_type=field_type,
                fill_instruction=fill_instruction,
                field_group_ids=[field_group.id]
            )

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


@router.post("/autofill/field_group/upsert", summary="创建或更新字段组（含批量字段）")
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
