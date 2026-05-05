"""
字段组管理接口
"""
import json

from fastapi import APIRouter, Header, Query
from tortoise.expressions import Q

from app.controllers.autofill import (
    field_group_config_controller,
    field_spec_controller,
    fill_page_controller,
)
from app.core.dependency import AuthControl, is_superuser, build_tenant_query
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.fill_page import FieldGroupConfigCreate, FieldGroupConfigUpdate
from app.services.autofill.prompt_service import (
    assemble_prompt,
    build_fields_instructions,
    build_function_schema,
)

router = APIRouter()


@router.get("/field_group/list", summary="字段组列表")
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

    tenant_query = build_tenant_query(current_user, tenant_id)
    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])

    total, groups = await field_group_config_controller.list(
        page=page, page_size=page_size, search=q, order=["-updated_at"]
    )
    data = [await obj.to_dict() for obj in groups]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/field_group/get", summary="字段组详情")
async def get_field_group(
    id: int = Query(..., description="字段组ID"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    group = await field_group_config_controller.get(id=id)
    return Success(data=await group.to_dict())


@router.get("/field_group/get_by_code", summary="通过编码获取字段组")
async def get_field_group_by_code(
    group_code: str = Query(..., description="字段组编码"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    group = await field_group_config_controller.get_by_code(code=group_code)
    if not group:
        return Fail(code=404, msg="字段组不存在")
    return Success(data=await group.to_dict())


@router.post("/field_group/create", summary="创建字段组")
async def create_field_group(
    group_in: FieldGroupConfigCreate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    page = await fill_page_controller.get(id=group_in.page_id)
    if not page:
        return Fail(code=400, msg="页面不存在")

    if is_superuser(current_user):
        target_tenant_id = group_in.tenant_id if group_in.tenant_id > 0 else page.tenant_id
    else:
        target_tenant_id = page.tenant_id
        if current_user.current_tenant_id > 0 and page.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权在该页面下创建字段组")

    group_in.tenant_id = target_tenant_id
    group_in.page_name = page.page_name
    group_in.app_name = page.app_name

    group = await field_group_config_controller.create_field_group(obj_in=group_in)
    return Success(data=await group.to_dict())


@router.post("/field_group/update", summary="更新字段组")
async def update_field_group(
    group_in: FieldGroupConfigUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    group = await field_group_config_controller.get(id=group_in.id)

    if not is_superuser(current_user):
        if group.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的字段组")

    if group_in.page_id > 0 and group_in.page_id != group.page_id:
        page = await fill_page_controller.get(id=group_in.page_id)
        if not page:
            return Fail(code=400, msg="页面不存在")
        group_in.page_name = page.page_name
        group_in.app_name = page.app_name

    updated = await field_group_config_controller.update_field_group(id=group_in.id, obj_in=group_in)
    return Success(data=await updated.to_dict())


@router.delete("/field_group/delete", summary="删除字段组")
async def delete_field_group(
    id: int = Query(..., description="字段组ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    group = await field_group_config_controller.get(id=id)

    if not is_superuser(current_user):
        if group.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的字段组")

    await field_group_config_controller.remove(id=id)
    return Success(msg="删除成功")


@router.get("/field_group/select", summary="字段组下拉列表")
async def get_field_group_select(
    page_id: int = Query(0, description="页面ID"),
    app_name: str = Query("", description="应用名称"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    q = Q(is_active=True)
    tenant_query = build_tenant_query(current_user, tenant_id)
    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])

    if page_id > 0:
        q &= Q(page_id=page_id)
    if app_name:
        q &= Q(app_name=app_name)

    groups = await field_group_config_controller.model.filter(q).all()
    data = [{"label": g.group_name, "value": g.id} for g in groups]
    return Success(data=data)


@router.get("/field_group/detail", summary="字段组详情（包含渲染后的Prompt和FC参数）")
async def get_field_group_detail(
    id: int = Query(..., description="字段组ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    group = await field_group_config_controller.get(id=id)
    if not group:
        return Fail(code=404, msg="字段组不存在")

    if not is_superuser(current_user):
        if group.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权查看其他租户的字段组")

    fields = await field_spec_controller.get_by_field_group(id)
    fields_instructions = build_fields_instructions(fields)
    function_schema = build_function_schema(group, fields)
    example_query = "[用户对话内容将在这里插入]"
    assembled_prompt = assemble_prompt(group, fields, example_query)

    result = {
        "basic_info": {
            "id": group.id,
            "group_name": group.group_name,
            "group_code": group.group_code,
            "app_name": group.app_name,
            "page_id": group.page_id,
            "page_name": group.page_name,
            "description": group.description,
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


@router.get("/field_group/export_md", summary="导出字段组配置为Markdown")
async def export_field_group_md(
    id: int = Query(..., description="字段组ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    group = await field_group_config_controller.get(id=id)
    if not group:
        return Fail(code=404, msg="字段组不存在")

    if not is_superuser(current_user):
        if group.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权查看其他租户的字段组")

    fields = await field_spec_controller.get_by_field_group(id)
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
    lines.append(f"**状态**: {'启用' if group.is_active else '禁用'}")
    lines.append("")

    if group.description:
        lines.append("## 描述")
        lines.append("")
        lines.append(group.description)
        lines.append("")

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

        if field.corrections:
            lines.append("")
            lines.append("**修正规则**:")
            for corr in field.corrections:
                lines.append(f"- {corr.get('text', '')}")

        lines.append("")

    lines.append("## Prompt模板")
    lines.append("")
    lines.append("### 基础模板")
    lines.append("")
    lines.append("```text")
    lines.append(group.prompt_template_base or "未配置")
    lines.append("```")
    lines.append("")

    fields_instructions = build_fields_instructions(fields)
    lines.append("### 字段指令")
    lines.append("")
    lines.append("```text")
    lines.append(fields_instructions)
    lines.append("```")
    lines.append("")

    function_schema = build_function_schema(group, fields)
    lines.append("## Function Calling Schema")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(function_schema, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")

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
