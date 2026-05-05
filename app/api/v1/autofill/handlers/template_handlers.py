"""
总结模板管理接口
"""
import csv
import io

from fastapi import APIRouter, File, Header, Query, UploadFile
from tortoise.expressions import Q

from app.controllers.autofill import summary_template_controller
from app.core.dependency import AuthControl, is_superuser, build_tenant_query
from app.schemas.autofill import SummaryTemplateCreate, SummaryTemplateUpdate
from app.schemas.base import Fail, Success, SuccessExtra

router = APIRouter()


@router.get("/template/list", summary="模板列表")
async def list_template(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    name: str = Query("", description="模板名称"),
    app_name: str = Query("", description="应用名称"),
    class_name: str = Query("", description="分类名称"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    q = Q()
    if name:
        q &= Q(name__contains=name)
    if app_name:
        q &= Q(app_name__contains=app_name)
    if class_name:
        q &= Q(class_name__contains=class_name)

    tenant_query = build_tenant_query(current_user, tenant_id)
    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])

    total, templates = await summary_template_controller.list(
        page=page, page_size=page_size, search=q, order=["-updated_at"]
    )
    data = [await obj.to_dict() for obj in templates]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/template/get", summary="模板详情")
async def get_template(
    id: int = Query(..., description="模板ID"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    template = await summary_template_controller.get(id=id)
    return Success(data=await template.to_dict())


@router.post("/template/create", summary="创建模板")
async def create_template(
    template_in: SummaryTemplateCreate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    target_tenant_id = 0
    if is_superuser(current_user):
        target_tenant_id = template_in.tenant_id
    else:
        target_tenant_id = current_user.current_tenant_id
        if target_tenant_id <= 0:
            return Fail(code=400, msg="您当前未选择租户，无法创建模板")

    template_in.tenant_id = target_tenant_id
    template = await summary_template_controller.create_template(obj_in=template_in)
    return Success(data=await template.to_dict())


@router.post("/template/update", summary="更新模板")
async def update_template(
    template_in: SummaryTemplateUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    template = await summary_template_controller.get(id=template_in.id)

    if not is_superuser(current_user):
        if template.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的模板")

    updated = await summary_template_controller.update_template(id=template_in.id, obj_in=template_in)
    return Success(data=await updated.to_dict())


@router.delete("/template/delete", summary="删除模板")
async def delete_template(
    id: int = Query(..., description="模板ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    template = await summary_template_controller.get(id=id)

    if not is_superuser(current_user):
        if template.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的模板")

    await summary_template_controller.remove(id=id)
    return Success(msg="删除成功")


@router.post("/template/import", summary="CSV批量导入总结模板")
async def import_template_from_csv(
    file: UploadFile = File(..., description="CSV文件"),
    app_name: str = Query(..., description="应用名称"),
    tenant_id: int = Query(None, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """
    CSV格式: name,class_name,summary,template_content
    """
    current_user = await AuthControl.is_authed(token)

    target_tenant_id = tenant_id
    if is_superuser(current_user):
        if target_tenant_id <= 0:
            return Fail(code=400, msg="请指定租户ID")
    else:
        target_tenant_id = current_user.current_tenant_id
        if target_tenant_id <= 0:
            return Fail(code=400, msg="您当前未选择租户")

    if not file.filename.endswith('.csv'):
        return Fail(code=400, msg="请上传CSV文件")

    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content_str))

        required_fields = ['name', 'class_name', 'template_content']
        if not csv_reader.fieldnames:
            return Fail(code=400, msg="CSV文件格式错误：无法读取表头")

        for field in required_fields:
            if field not in csv_reader.fieldnames:
                return Fail(code=400, msg=f"CSV文件缺少必填字段: {field}")

        rows = list(csv_reader)
        created_count = 0
        updated_count = 0
        errors = []

        for idx, row in enumerate(rows, start=2):
            try:
                name = row.get('name', '').strip()
                class_name = row.get('class_name', '').strip()
                summary = row.get('summary', '').strip()
                template_content = row.get('template_content', '').strip()

                if not name:
                    errors.append(f"第{idx}行: 模板名称不能为空")
                    continue
                if not class_name:
                    errors.append(f"第{idx}行: 分类名称不能为空")
                    continue
                if not template_content:
                    errors.append(f"第{idx}行: 模板内容不能为空")
                    continue

                existing = await summary_template_controller.model.filter(
                    tenant_id=target_tenant_id,
                    app_name=app_name,
                    class_name=class_name,
                    name=name
                ).first()

                if existing:
                    existing.summary = summary
                    existing.template_content = template_content
                    await existing.save()
                    updated_count += 1
                else:
                    await summary_template_controller.model.create(
                        tenant_id=target_tenant_id,
                        app_name=app_name,
                        class_name=class_name,
                        name=name,
                        summary=summary,
                        template_content=template_content
                    )
                    created_count += 1

            except Exception as e:
                errors.append(f"第{idx}行: {str(e)}")

        result = {
            "created": created_count,
            "updated": updated_count,
            "total": len(rows),
            "errors": errors
        }

        if errors:
            return Success(data=result, msg=f"导入完成，但有{len(errors)}个错误")
        return Success(data=result, msg="导入成功")

    except Exception as e:
        return Fail(code=500, msg=f"导入失败: {str(e)}")
