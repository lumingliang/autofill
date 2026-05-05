import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Header, Query
from tortoise.expressions import Q

from app.controllers.autofill import (
    app_management_controller,
    field_group_config_controller,
    field_spec_controller,
    fill_page_controller,
)
from app.models.autofill import FieldGroupFieldSpec
from app.core.dependency import AuthControl, is_superuser, build_tenant_query
from app.models.admin import User
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.fill_page import (
    FieldGroupConfigCreate,
    FieldGroupConfigUpdate,
    FieldSpecCreate,
    FieldSpecUpdate,
    FillPageCreate,
    FillPageUpdate,
    SwaggerSyncRequest,
)
from app.services.autofill.prompt_service import (
    assemble_prompt,
    build_fields_instructions,
    build_function_schema,
)

# 创建路由
page_router = APIRouter()
field_group_router = APIRouter()
field_spec_router = APIRouter()


# ==================== 填单页面管理接口 ====================

@page_router.get("/page/list", summary="页面列表")
async def list_page(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    page_name: str = Query("", description="页面名称"),
    page_code: str = Query("", description="页面编码"),
    app_name: str = Query("", description="应用名称"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    q = Q()
    if page_name:
        q &= Q(page_name__contains=page_name)
    if page_code:
        q &= Q(page_code__contains=page_code)
    if app_name:
        q &= Q(app_name__contains=app_name)

    # 多租户筛选
    tenant_query = build_tenant_query(current_user, tenant_id)
    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])

    total, pages = await fill_page_controller.list(
        page=page, page_size=page_size, search=q, order=["-updated_at"]
    )
    data = [await obj.to_dict() for obj in pages]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@page_router.get("/page/get", summary="页面详情")
async def get_page(
    id: int = Query(..., description="页面ID"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    page = await fill_page_controller.get(id=id)
    return Success(data=await page.to_dict())


@page_router.post("/page/create", summary="创建页面")
async def create_page(
    page_in: FillPageCreate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    # 验证应用是否存在
    app = await app_management_controller.model.filter(app_name=page_in.app_name).first()
    if not app:
        return Fail(code=400, msg=f"应用 '{page_in.app_name}' 不存在")

    # 确定租户ID：优先从应用继承，如果是超级用户可覆盖
    if is_superuser(current_user):
        # 超级用户：如果请求指定了租户ID则使用，否则从应用继承
        target_tenant_id = page_in.tenant_id if page_in.tenant_id > 0 else app.tenant_id
    else:
        # 普通用户：必须使用应用绑定的租户ID
        target_tenant_id = app.tenant_id
        if current_user.current_tenant_id > 0 and app.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权在该应用下创建页面")

    # 使用确定的租户ID和应用ID
    page_in.tenant_id = target_tenant_id
    # 设置 app_id 用于数据库关联
    page_in.app_id = app.id

    page = await fill_page_controller.create_page(obj_in=page_in)
    return Success(data=await page.to_dict())


@page_router.post("/page/update", summary="更新页面")
async def update_page(
    page_in: FillPageUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    page = await fill_page_controller.get(id=page_in.id)

    # 权限检查
    if not is_superuser(current_user):
        if page.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的页面")

    # 如果修改了应用名称，验证新应用是否存在
    if page_in.app_name and page_in.app_name != page.app_name:
        app = await app_management_controller.model.filter(app_name=page_in.app_name).first()
        if not app:
            return Fail(code=400, msg=f"应用 '{page_in.app_name}' 不存在")
        # 设置 app_id 用于数据库关联
        page_in.app_id = app.id

    updated = await fill_page_controller.update_page(id=page_in.id, obj_in=page_in)
    return Success(data=await updated.to_dict())


@page_router.delete("/page/delete", summary="删除页面")
async def delete_page(
    id: int = Query(..., description="页面ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    page = await fill_page_controller.get(id=id)

    # 权限检查
    if not is_superuser(current_user):
        if page.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的页面")

    await fill_page_controller.remove(id=id)
    return Success(msg="删除成功")


@page_router.get("/page/select", summary="页面下拉列表")
async def get_page_select(
    app_name: str = Query("", description="应用名称"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """
    获取页面下拉列表，供其他模块使用
    """
    current_user = await AuthControl.is_authed(token)

    q = Q(is_active=True)

    # 多租户筛选
    tenant_query = build_tenant_query(current_user, tenant_id)
    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])

    if app_name:
        q &= Q(app_name=app_name)

    pages = await fill_page_controller.model.filter(q).all()
    data = [{"label": f"{p.page_name} ({p.page_code})", "value": p.id} for p in pages]
    return Success(data=data)


# ==================== 字段组配置管理接口 ====================

@field_group_router.get("/field_group/list", summary="字段组列表")
async def list_field_group(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    group_name: str = Query("", description="字段组名称"),
    app_name: str = Query("", description="应用名称"),
    page_id: int = Query(0, description="页面ID"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    q = Q()
    if group_name:
        q &= Q(group_name__contains=group_name)
    if app_name:
        q &= Q(app_name__contains=app_name)
    if page_id > 0:
        q &= Q(page_id=page_id)

    # 多租户筛选
    tenant_query = build_tenant_query(current_user, tenant_id)
    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])

    total, groups = await field_group_config_controller.list(
        page=page, page_size=page_size, search=q, order=["-updated_at"]
    )
    data = [await obj.to_dict() for obj in groups]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@field_group_router.get("/field_group/get", summary="字段组详情")
async def get_field_group(
    id: int = Query(..., description="字段组ID"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    group = await field_group_config_controller.get(id=id)
    return Success(data=await group.to_dict())


@field_group_router.get("/field_group/get_by_code", summary="通过编码获取字段组")
async def get_field_group_by_code(
    group_code: str = Query(..., description="字段组编码"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    group = await field_group_config_controller.get_by_code(code=group_code)
    if not group:
        return Fail(code=404, msg="字段组不存在")
    return Success(data=await group.to_dict())


@field_group_router.post("/field_group/create", summary="创建字段组")
async def create_field_group(
    group_in: FieldGroupConfigCreate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    # 验证页面是否存在
    page = await fill_page_controller.get(id=group_in.page_id)
    if not page:
        return Fail(code=400, msg="页面不存在")

    # 确定租户ID：必须从页面继承（页面已从应用继承）
    if is_superuser(current_user):
        # 超级用户：如果请求指定了租户ID则使用，否则从页面继承
        target_tenant_id = group_in.tenant_id if group_in.tenant_id > 0 else page.tenant_id
    else:
        # 普通用户：必须使用页面绑定的租户ID
        target_tenant_id = page.tenant_id
        if current_user.current_tenant_id > 0 and page.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权在该页面下创建字段组")

    # 使用确定的租户ID和页面信息（自动继承页面的app_name和tenant_id）
    group_in.tenant_id = target_tenant_id
    group_in.page_name = page.page_name
    group_in.app_name = page.app_name

    group = await field_group_config_controller.create_field_group(obj_in=group_in)
    return Success(data=await group.to_dict())


@field_group_router.post("/field_group/update", summary="更新字段组")
async def update_field_group(
    group_in: FieldGroupConfigUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    group = await field_group_config_controller.get(id=group_in.id)

    # 权限检查
    if not is_superuser(current_user):
        if group.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的字段组")

    # 如果修改了页面ID，验证新页面是否存在
    if group_in.page_id > 0 and group_in.page_id != group.page_id:
        page = await fill_page_controller.get(id=group_in.page_id)
        if not page:
            return Fail(code=400, msg="页面不存在")
        group_in.page_name = page.page_name
        group_in.app_name = page.app_name

    updated = await field_group_config_controller.update_field_group(id=group_in.id, obj_in=group_in)
    return Success(data=await updated.to_dict())


@field_group_router.delete("/field_group/delete", summary="删除字段组")
async def delete_field_group(
    id: int = Query(..., description="字段组ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    group = await field_group_config_controller.get(id=id)

    # 权限检查
    if not is_superuser(current_user):
        if group.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的字段组")

    await field_group_config_controller.remove(id=id)
    return Success(msg="删除成功")


@field_group_router.get("/field_group/select", summary="字段组下拉列表")
async def get_field_group_select(
    page_id: int = Query(0, description="页面ID"),
    app_name: str = Query("", description="应用名称"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """
    获取字段组下拉列表，供其他模块使用
    """
    current_user = await AuthControl.is_authed(token)

    q = Q(is_active=True)

    # 多租户筛选
    tenant_query = build_tenant_query(current_user, tenant_id)
    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])

    if page_id > 0:
        q &= Q(page_id=page_id)
    if app_name:
        q &= Q(app_name=app_name)

    groups = await field_group_config_controller.model.filter(q).all()
    data = [{"label": g.field_group_name, "value": g.id} for g in groups]
    return Success(data=data)


# ==================== 字段明细管理接口 ====================

@field_spec_router.get("/field_spec/list", summary="字段明细列表")
async def list_field_spec(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    field_name: str = Query("", description="字段名"),
    field_label: str = Query("", description="字段标签"),
    field_type: str = Query("", description="字段类型"),
    field_group_id: int = Query(0, description="字段组ID"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    # 多租户筛选
    tenant_query = build_tenant_query(current_user, tenant_id)

    # 如果指定了字段组ID，通过中间表查询关联的字段ID
    if field_group_id > 0:
        # 构建中间表查询条件
        relation_q = Q(field_group_id=field_group_id)
        if tenant_query["tenant_id"] > 0:
            relation_q &= Q(tenant_id=tenant_query["tenant_id"])
        relations = await FieldGroupFieldSpec.filter(relation_q).all()
        field_spec_ids = [r.field_spec_id for r in relations]
        if not field_spec_ids:
            return SuccessExtra(data=[], total=0, page=page, page_size=page_size)
        q = Q(id__in=field_spec_ids)
    else:
        q = Q()

    if field_name:
        q &= Q(field_name__contains=field_name)
    if field_label:
        q &= Q(field_label__contains=field_label)
    if field_type:
        q &= Q(field_type=field_type)

    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])

    total, specs = await field_spec_controller.list(
        page=page, page_size=page_size, search=q, order=["-updated_at"]
    )

    # 获取字段关联的字段组信息
    data = []
    for spec in specs:
        spec_dict = await spec.to_dict()
        # 通过中间表查询关联的字段组
        relations = await FieldGroupFieldSpec.filter(field_spec_id=spec.id).all()
        group_ids = [r.field_group_id for r in relations]
        spec_dict['field_group_ids'] = group_ids
        # 获取字段组基本信息
        groups = await field_group_config_controller.model.filter(id__in=group_ids).all()
        spec_dict['field_groups'] = [
            {"id": g.id, "group_name": g.group_name, "group_code": g.group_code}
            for g in groups
        ]
        data.append(spec_dict)

    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@field_spec_router.get("/field_spec/get", summary="字段明细详情")
async def get_field_spec(
    id: int = Query(..., description="字段明细ID"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    spec = await field_spec_controller.get(id=id)
    spec_dict = await spec.to_dict()

    # 通过中间表查询关联的字段组
    relations = await FieldGroupFieldSpec.filter(field_spec_id=spec.id).all()
    group_ids = [r.field_group_id for r in relations]
    spec_dict['field_group_ids'] = group_ids

    # 获取字段组基本信息
    groups = await field_group_config_controller.model.filter(id__in=group_ids).all()
    spec_dict['field_groups'] = [
        {"id": g.id, "group_name": g.group_name, "group_code": g.group_code}
        for g in groups
    ]

    return Success(data=spec_dict)


@field_spec_router.post("/field_spec/create", summary="创建字段明细")
async def create_field_spec(
    spec_in: FieldSpecCreate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    # 验证关联的字段组是否存在且有权限
    if not spec_in.field_group_ids:
        return Fail(code=400, msg="必须至少选择一个字段组")

    first_group = None
    for group_id in spec_in.field_group_ids:
        group = await field_group_config_controller.get(id=group_id)
        if not group:
            return Fail(code=400, msg=f"字段组(ID:{group_id})不存在")
        if not is_superuser(current_user):
            if group.tenant_id != current_user.current_tenant_id:
                return Fail(code=403, msg=f"无权操作字段组(ID:{group_id})")
        if not first_group:
            first_group = group

    # 从第一个字段组继承租户ID和应用名称
    # 字段组已从页面继承，页面已从应用继承
    if is_superuser(current_user):
        # 超级用户：如果请求指定了租户ID则使用，否则从字段组继承
        target_tenant_id = spec_in.tenant_id if spec_in.tenant_id > 0 else first_group.tenant_id
        target_app_name = spec_in.app_name if spec_in.app_name else first_group.app_name
    else:
        # 普通用户：必须使用字段组绑定的租户ID和应用名称
        target_tenant_id = first_group.tenant_id
        target_app_name = first_group.app_name
        if current_user.current_tenant_id > 0 and first_group.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权在该字段组下创建字段")

    # 创建字段
    spec = await field_spec_controller.create_field_spec(
        obj_in=spec_in,
        tenant_id=target_tenant_id,
        app_name=target_app_name
    )

    # 返回完整数据
    spec_dict = await spec.to_dict()
    relations = await FieldGroupFieldSpec.filter(field_spec_id=spec.id).all()
    group_ids = [r.field_group_id for r in relations]
    spec_dict['field_group_ids'] = group_ids
    groups = await field_group_config_controller.model.filter(id__in=group_ids).all()
    spec_dict['field_groups'] = [
        {"id": g.id, "group_name": g.group_name, "group_code": g.group_code}
        for g in groups
    ]

    return Success(data=spec_dict)


@field_spec_router.post("/field_spec/update", summary="更新字段明细")
async def update_field_spec(
    spec_in: FieldSpecUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    spec = await field_spec_controller.get(id=spec_in.id)

    # 权限检查 - 检查字段本身的租户权限
    if not is_superuser(current_user):
        if spec.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的字段")

    # 如果更新了关联字段组，验证权限
    if spec_in.field_group_ids:
        for group_id in spec_in.field_group_ids:
            group = await field_group_config_controller.get(id=group_id)
            if not group:
                return Fail(code=400, msg=f"字段组(ID:{group_id})不存在")
            if not is_superuser(current_user):
                if group.tenant_id != current_user.current_tenant_id:
                    return Fail(code=403, msg=f"无权操作字段组(ID:{group_id})")

    updated = await field_spec_controller.update_field_spec(
        id=spec_in.id,
        obj_in=spec_in,
        tenant_id=spec.tenant_id,
        app_name=spec.app_name
    )

    # 返回完整数据
    spec_dict = await updated.to_dict()
    relations = await FieldGroupFieldSpec.filter(field_spec_id=updated.id).all()
    group_ids = [r.field_group_id for r in relations]
    spec_dict['field_group_ids'] = group_ids
    groups = await field_group_config_controller.model.filter(id__in=group_ids).all()
    spec_dict['field_groups'] = [
        {"id": g.id, "group_name": g.group_name, "group_code": g.group_code}
        for g in groups
    ]

    return Success(data=spec_dict)


@field_spec_router.delete("/field_spec/delete", summary="删除字段明细")
async def delete_field_spec(
    id: int = Query(..., description="字段明细ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    spec = await field_spec_controller.get(id=id)

    # 权限检查 - 检查字段本身的租户权限
    if not is_superuser(current_user):
        if spec.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的字段")

    await field_spec_controller.delete_field_spec(id=id)
    return Success(msg="删除成功")


@field_spec_router.get("/field_spec/by_group", summary="获取字段组下的所有字段")
async def get_field_specs_by_group(
    field_group_id: int = Query(..., description="字段组ID"),
    token: str = Header(..., description="token验证"),
):
    """
    获取指定字段组下的所有字段明细
    """
    current_user = await AuthControl.is_authed(token)

    # 验证字段组是否存在
    group = await field_group_config_controller.get(id=field_group_id)
    if not group:
        return Fail(code=400, msg="字段组不存在")

    # 权限检查
    if not is_superuser(current_user):
        if group.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权查看其他租户的字段")

    fields = await field_spec_controller.get_by_field_group(field_group_id)
    data = [await obj.to_dict() for obj in fields]
    return Success(data=data)


# ==================== 字段组详情展示接口（包含Prompt和FC参数）====================

@field_group_router.get("/field_group/detail", summary="字段组详情（包含渲染后的Prompt和FC参数）")
async def get_field_group_detail(
    id: int = Query(..., description="字段组ID"),
    token: str = Header(..., description="token验证"),
):
    """
    获取字段组详细信息，包含：
    1. 字段组基本信息
    2. 字段明细列表
    3. 渲染后的Prompt模板（使用示例query）
    4. Function Calling Schema
    5. 字段指令说明
    """
    current_user = await AuthControl.is_authed(token)

    # 获取字段组
    group = await field_group_config_controller.get(id=id)
    if not group:
        return Fail(code=404, msg="字段组不存在")

    # 权限检查
    if not is_superuser(current_user):
        if group.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权查看其他租户的字段组")

    # 获取字段明细
    fields = await field_spec_controller.get_by_field_group(id)

    # 构建字段指令
    fields_instructions = build_fields_instructions(fields)

    # 构建Function Calling Schema
    function_schema = build_function_schema(group, fields)

    # 组装示例Prompt（使用占位符query）
    example_query = "[用户对话内容将在这里插入]"
    assembled_prompt = assemble_prompt(group, fields, example_query)

    # 构建返回数据
    result = {
        "basic_info": {
            "id": group.id,
            "group_name": group.group_name,
            "group_code": group.group_code,
            "app_name": group.app_name,
            "page_id": group.page_id,
            "page_name": group.page_name,
            "description": group.description,
            "version": group.version,
            "is_active": group.is_active,
            "created_at": str(group.created_at) if group.created_at else None,
            "updated_at": str(group.updated_at) if group.updated_at else None,
        },
        "field_specs": [await obj.to_dict() for obj in fields],
        "prompt_info": {
            "template_base": group.prompt_template_base,
            "fields_instructions": fields_instructions,
            "assembled_prompt": assembled_prompt,
        },
        "function_calling": {
            "schema": function_schema,
            "json_schema": json.dumps(function_schema, ensure_ascii=False, indent=2),
        },
        "output_templates": group.output_templates or {},
    }

    return Success(data=result)


@field_group_router.get("/field_group/export_md", summary="导出字段组配置为Markdown")
async def export_field_group_md(
    id: int = Query(..., description="字段组ID"),
    token: str = Header(..., description="token验证"),
):
    """
    将字段组配置导出为人类可读的Markdown格式
    """
    current_user = await AuthControl.is_authed(token)

    # 获取字段组
    group = await field_group_config_controller.get(id=id)
    if not group:
        return Fail(code=404, msg="字段组不存在")

    # 权限检查
    if not is_superuser(current_user):
        if group.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权查看其他租户的字段组")

    # 获取字段明细
    fields = await field_spec_controller.get_by_field_group(id)

    # 构建Markdown内容
    md_content = _build_field_group_markdown(group, fields)

    return Success(data={
        "markdown": md_content,
        "filename": f"field_group_{group.group_code}.md"
    })


def _build_field_group_markdown(group, fields) -> str:
    """构建字段组的Markdown文档"""

    lines = []
    lines.append(f"# {group.group_name}")
    lines.append("")
    lines.append(f"**编码**: `{group.group_code}`")
    lines.append(f"**应用**: {group.app_name}")
    lines.append(f"**页面**: {group.page_name}")
    lines.append(f"**版本**: v{group.version}")
    lines.append(f"**状态**: {'启用' if group.is_active else '禁用'}")
    lines.append("")

    if group.description:
        lines.append("## 描述")
        lines.append("")
        lines.append(group.description)
        lines.append("")

    # 字段明细
    lines.append("## 字段明细")
    lines.append("")
    lines.append(f"共 {len(fields)} 个字段")
    lines.append("")

    for i, field in enumerate(fields, 1):
        lines.append(f"### {i}. {field.field_label}")
        lines.append("")
        lines.append(f"- **字段名**: `{field.field_name}`")
        lines.append(f"- **类型**: {field.field_type.value}")
        lines.append(f"- **状态**: {'启用' if field.is_active else '禁用'}")

        if field.fill_instruction:
            lines.append(f"- **填写说明**: {field.fill_instruction}")

        # Select类型选项
        if field.field_type.value == 'select' and field.options:
            items = field.options.get('items', [])
            if items:
                lines.append("")
                lines.append("**选项列表**:")
                lines.append("")
                lines.append("| 值 | 标签 | 说明 |")
                lines.append("|---|---|---|")
                for opt in items:
                    if not opt.get('is_deleted', False):
                        value = opt.get('value', '')
                        label = opt.get('label', '')
                        annotation = opt.get('base_annotation', '')
                        lines.append(f"| {value} | {label} | {annotation} |")

        # 修正规则
        if field.corrections:
            lines.append("")
            lines.append("**修正规则**:")
            for corr in field.corrections:
                lines.append(f"- {corr.get('text', '')}")

        lines.append("")

    # Prompt模板
    lines.append("## Prompt模板")
    lines.append("")
    lines.append("### 基础模板")
    lines.append("")
    lines.append("```text")
    lines.append(group.prompt_template_base or "未配置")
    lines.append("```")
    lines.append("")

    # 字段指令
    fields_instructions = build_fields_instructions(fields)
    lines.append("### 字段指令")
    lines.append("")
    lines.append("```text")
    lines.append(fields_instructions)
    lines.append("```")
    lines.append("")

    # Function Calling Schema
    function_schema = build_function_schema(group, fields)
    lines.append("## Function Calling Schema")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(function_schema, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")

    # 输出模板
    if group.output_templates:
        lines.append("## 输出模板")
        lines.append("")
        for template_name, template_data in group.output_templates.items():
            if isinstance(template_data, dict):
                template_desc = template_data.get('description', '')
                template_content = template_data.get('template', '')
            else:
                template_desc = ''
                template_content = str(template_data)

            lines.append(f"### {template_name}")
            if template_desc:
                lines.append(f"*{template_desc}*")
            lines.append("")
            lines.append("```text")
            lines.append(template_content)
            lines.append("```")
            lines.append("")

    return "\n".join(lines)


# ==================== 页面管理详情接口 ====================

@page_router.get("/page/detail", summary="页面详情（包含关联字段组）")
async def get_page_detail(
    id: int = Query(..., description="页面ID"),
    token: str = Header(..., description="token验证"),
):
    """
    获取页面详细信息，包含关联的字段组列表
    """
    current_user = await AuthControl.is_authed(token)

    # 获取页面
    page = await fill_page_controller.get(id=id)
    if not page:
        return Fail(code=404, msg="页面不存在")

    # 权限检查
    if not is_superuser(current_user):
        if page.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权查看其他租户的页面")

    # 获取关联的字段组
    field_groups = await field_group_config_controller.model.filter(
        page_id=id, is_active=True
    ).all()

    # 构建返回数据
    result = {
        "basic_info": await page.to_dict(),
        "field_groups": [],
    }

    for group in field_groups:
        # 获取字段数量
        field_count = await field_spec_controller.model.filter(
            field_group_id=group.id, is_active=True
        ).count()

        result["field_groups"].append({
            "id": group.id,
            "group_name": group.group_name,
            "group_code": group.group_code,
            "description": group.description,
            "version": group.version,
            "field_count": field_count,
            "updated_at": str(group.updated_at) if group.updated_at else None,
        })

    return Success(data=result)


@page_router.get("/page/export_md", summary="导出页面配置为Markdown")
async def export_page_md(
    id: int = Query(..., description="页面ID"),
    token: str = Header(..., description="token验证"),
):
    """
    将页面配置及关联字段组导出为人类可读的Markdown格式
    """
    current_user = await AuthControl.is_authed(token)

    # 获取页面
    page = await fill_page_controller.get(id=id)
    if not page:
        return Fail(code=404, msg="页面不存在")

    # 权限检查
    if not is_superuser(current_user):
        if page.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权查看其他租户的页面")

    # 获取关联的字段组
    field_groups = await field_group_config_controller.model.filter(
        page_id=id, is_active=True
    ).all()

    # 构建Markdown内容
    md_content = _build_page_markdown(page, field_groups)

    return Success(data={
        "markdown": md_content,
        "filename": f"page_{page.page_code}.md"
    })


def _build_page_markdown(page, field_groups) -> str:
    """构建页面的Markdown文档"""

    lines = []
    lines.append(f"# {page.page_name}")
    lines.append("")
    lines.append(f"**编码**: `{page.page_code}`")
    lines.append(f"**应用**: {page.app_name}")
    lines.append(f"**状态**: {'启用' if page.is_active else '禁用'}")
    lines.append("")

    if page.description:
        lines.append("## 描述")
        lines.append("")
        lines.append(page.description)
        lines.append("")

    # 字段组列表
    lines.append("## 字段组列表")
    lines.append("")
    lines.append(f"共 {len(field_groups)} 个字段组")
    lines.append("")

    for i, group in enumerate(field_groups, 1):
        lines.append(f"### {i}. {group.group_name}")
        lines.append("")
        lines.append(f"- **编码**: `{group.group_code}`")
        lines.append(f"- **版本**: v{group.version}")
        lines.append(f"- **状态**: {'启用' if group.is_active else '禁用'}")

        if group.description:
            lines.append(f"- **描述**: {group.description}")

        lines.append("")

        # 输出模板预览
        if group.output_templates:
            lines.append("**输出模板**:")
            lines.append("")
            for template_name in group.output_templates.keys():
                lines.append(f"- {template_name}")
            lines.append("")

    return "\n".join(lines)


# ==================== Swagger 同步接口 ====================

@field_spec_router.post("/field_spec/sync_swagger", summary="同步 Swagger 文档并解析为选项")
async def sync_swagger_document(
    sync_in: SwaggerSyncRequest,
    token: str = Header(..., description="token验证"),
):
    """
    同步 OpenAI Swagger JSON 文档，解析 API 端点并生成选项列表
    """
    from app.services.agent_v2.openapi_parser import OpenAPIParser
    from datetime import datetime

    current_user = await AuthControl.is_authed(token)

    # 获取字段明细
    spec = await field_spec_controller.get(id=sync_in.field_spec_id)
    if not spec:
        return Fail(code=404, msg="字段明细不存在")

    # 获取字段组进行权限检查
    group = await field_group_config_controller.get(id=spec.field_group_id)
    if not group:
        return Fail(code=400, msg="字段组不存在")

    # 权限检查
    if not is_superuser(current_user):
        if group.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的字段")

    # 验证字段类型必须是 select
    if spec.field_type != "select":
        return Fail(code=400, msg="只有下拉选择类型的字段才支持 Swagger 同步")

    try:
        # 解析 Swagger JSON
        parser = OpenAPIParser(sync_in.swagger_json)
        endpoints = parser.get_endpoints()

        if not endpoints:
            return Fail(code=400, msg="未能从 Swagger 文档中解析出任何 API 端点")

        # 将端点转换为选项列表
        option_items = []
        for endpoint in endpoints:
            # 使用 operation_id 或生成一个标识
            value = endpoint.operation_id or f"{endpoint.method}_{endpoint.path.replace('/', '_')}"
            # 使用 summary 或 description 作为标签
            label = endpoint.summary or endpoint.description or f"{endpoint.method.upper()} {endpoint.path}"
            # 构建详细说明
            base_annotation = f"{endpoint.method.upper()} {endpoint.path}"
            if endpoint.description:
                base_annotation += f"\n{endpoint.description}"

            option_items.append({
                "value": value,
                "label": label,
                "base_annotation": base_annotation,
                "corrections": [],
                "is_deleted": False,
            })

        # 更新字段的 options
        current_options = spec.options or {}
        current_options["source"] = "api"
        current_options["items"] = option_items
        current_options["swagger_json"] = sync_in.swagger_json
        current_options["appkey"] = sync_in.appkey
        current_options["last_sync_at"] = datetime.now().isoformat()
        current_options["sync_endpoints_count"] = len(endpoints)

        # 保存更新
        spec.options = current_options
        await spec.save()

        return Success(data={
            "success": True,
            "message": f"成功同步 {len(endpoints)} 个 API 端点",
            "synced_count": len(endpoints),
            "endpoints": [ep.to_dict() for ep in endpoints],
        })

    except Exception as e:
        return Fail(code=500, msg=f"同步失败: {str(e)}")
