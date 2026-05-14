"""
页面管理接口
"""
from fastapi import APIRouter, Header, Query
from tortoise.expressions import Q

from app.controllers.autofill import (
    app_management_controller,
    field_group_config_controller,
    field_spec_controller,
    fill_page_controller,
)
from app.models.autofill import FieldGroupFieldSpec
from app.core.dependency import AuthControl, is_superuser, build_tenant_query, TenantControl
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.fill_page import FillPageCreate, FillPageUpdate

router = APIRouter()


@router.get("/page/list", summary="页面列表")
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

    tenant_query = build_tenant_query(current_user, tenant_id)
    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])

    total, pages = await fill_page_controller.list(
        page=page, page_size=page_size, search=q, order=["-updated_at"]
    )
    data = [await obj.to_dict() for obj in pages]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/page/get", summary="页面详情")
async def get_page(
    id: int = Query(..., description="页面ID"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    page = await fill_page_controller.get(id=id)
    return Success(data=await page.to_dict())


@router.post("/page/create", summary="创建页面")
async def create_page(
    page_in: FillPageCreate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    app = await app_management_controller.model.filter(app_name=page_in.app_name).first()
    if not app:
        return Fail(code=400, msg=f"应用 '{page_in.app_name}' 不存在")

    # 使用公共方法验证租户ID
    success, msg, effective_tenant_id = TenantControl.validate_create_tenant_id(
        current_user, page_in.tenant_id
    )
    if not success:
        return Fail(code=400, msg=msg)
    
    # 如果超管没传tenant_id，使用应用的租户
    if is_superuser(current_user) and page_in.tenant_id <= 0:
        effective_tenant_id = app.tenant_id
    
    page_in.tenant_id = effective_tenant_id
    page_in.app_id = app.id

    page = await fill_page_controller.create_page(obj_in=page_in)
    return Success(data=await page.to_dict())


@router.post("/page/update", summary="更新页面")
async def update_page(
    page_in: FillPageUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    page = await fill_page_controller.get(id=page_in.id)

    if not is_superuser(current_user):
        if page.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的页面")

    if page_in.app_name and page_in.app_name != page.app_name:
        app = await app_management_controller.model.filter(app_name=page_in.app_name).first()
        if not app:
            return Fail(code=400, msg=f"应用 '{page_in.app_name}' 不存在")
        page_in.app_id = app.id

    updated = await fill_page_controller.update_page(id=page_in.id, obj_in=page_in)
    return Success(data=await updated.to_dict())


@router.delete("/page/delete", summary="删除页面")
async def delete_page(
    id: int = Query(..., description="页面ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    page = await fill_page_controller.get(id=id)

    # 使用公共方法验证删除权限
    success, msg = TenantControl.validate_delete_permission(
        current_user, page.tenant_id
    )
    if not success:
        return Fail(code=403, msg=msg)

    await fill_page_controller.remove(id=id)
    return Success(msg="删除成功")


@router.get("/page/select", summary="页面下拉列表")
async def get_page_select(
    app_name: str = Query("", description="应用名称"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    q = Q(is_active=True)
    tenant_query = build_tenant_query(current_user, tenant_id)
    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])

    if app_name:
        q &= Q(app_name=app_name)

    pages = await fill_page_controller.model.filter(q).all()
    data = [{"label": f"{p.page_name} ({p.page_code})", "value": p.id} for p in pages]
    return Success(data=data)


@router.get("/page/detail", summary="页面详情（包含关联字段组）")
async def get_page_detail(
    id: int = Query(..., description="页面ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    page = await fill_page_controller.get(id=id)
    if not page:
        return Fail(code=404, msg="页面不存在")

    if not is_superuser(current_user):
        if page.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权查看其他租户的页面")

    field_groups = await field_group_config_controller.model.filter(
        page_id=id, is_active=True
    ).all()

    result = {
        "basic_info": await page.to_dict(),
        "field_groups": [],
    }

    for group in field_groups:
        # 获取字段数（通过中间表查询）
        field_count = await FieldGroupFieldSpec.filter(
            field_group_id=group.id
        ).count()

        result["field_groups"].append({
            "id": group.id,
            "group_name": group.group_name,
            "group_code": group.group_code,
            "description": group.description,
            "is_active": group.is_active,
            "field_count": field_count,
            "updated_at": str(group.updated_at) if group.updated_at else None,
        })

    return Success(data=result)


@router.get("/page/export_md", summary="导出页面配置为Markdown")
async def export_page_md(
    id: int = Query(..., description="页面ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    page = await fill_page_controller.get(id=id)
    if not page:
        return Fail(code=404, msg="页面不存在")

    if not is_superuser(current_user):
        if page.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权查看其他租户的页面")

    field_groups = await field_group_config_controller.model.filter(
        page_id=id, is_active=True
    ).all()

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

    lines.append("## 字段组列表")
    lines.append("")
    lines.append(f"共 {len(field_groups)} 个字段组")
    lines.append("")

    for i, group in enumerate(field_groups, 1):
        lines.append(f"### {i}. {group.group_name}")
        lines.append("")
        lines.append(f"- **编码**: `{group.group_code}`")
        lines.append(f"- **状态**: {'启用' if group.is_active else '禁用'}")

        if group.description:
            lines.append(f"- **描述**: {group.description}")

        lines.append("")

        if group.output_templates:
            lines.append("**输出模板**:")
            lines.append("")
            for template_name in group.output_templates.keys():
                lines.append(f"- {template_name}")
            lines.append("")

    return "\n".join(lines)
