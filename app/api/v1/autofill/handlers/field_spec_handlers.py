"""
字段明细管理接口
"""
from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, Header, Query
from pydantic import BaseModel, Field
from tortoise.expressions import Q

from app.controllers.autofill import field_group_config_controller, field_spec_controller
from app.core.dependency import AuthControl, TenantControl
from app.core.tenant import TenantContext
from app.models.autofill import FieldGroupFieldSpec, FieldGroupConfig, FieldSpec
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.fill_page import (
    FieldSpecCreate, FieldSpecUpdate,
    FlattenConfig
)
from app.services.autofill.field_spec_service import upsert_field_spec

router = APIRouter()


@router.get("/field_spec/list", summary="字段明细列表")
async def list_field_spec(
    page: int = Query(1),
    page_size: int = Query(10),
    field_name: str = Query(""),
    field_label: str = Query(""),
    field_type: str = Query(""),
    app_name: str = Query(""),
    tenant_id: int = Query(0),
    field_group_id: int = Query(0, description="字段组ID，用于筛选特定字段组下的字段"),
    token: str = Header(...),
):
    await AuthControl.is_authed(token)
    tenant_filter = TenantContext.build_query_filter(tenant_id)

    # 如果指定了字段组ID，先获取该字段组下的所有字段ID
    field_spec_ids = None
    if field_group_id > 0:
        relations = await FieldGroupFieldSpec.filter(field_group_id=field_group_id).all()
        field_spec_ids = [r.field_spec_id for r in relations]
        if not field_spec_ids:
            return SuccessExtra(data=[], total=0, page=page, page_size=page_size)

    q = Q()

    if field_name:
        q &= Q(field_name__contains=field_name)
    if field_label:
        q &= Q(field_label__contains=field_label)
    if field_type:
        q &= Q(field_type=field_type)
    if app_name:
        q &= Q(app_name=app_name)
    if field_spec_ids:
        q &= Q(id__in=field_spec_ids)
    if tenant_filter:
        q &= Q(**tenant_filter)

    total, specs = await field_spec_controller.list(page=page, page_size=page_size, search=q, order=["-updated_at"])

    data = []
    for spec in specs:
        spec_dict = await spec.to_dict()
        data.append(spec_dict)

    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/field_spec/get", summary="字段明细详情")
async def get_field_spec(id: int = Query(...), token: str = Header(...)):
    await AuthControl.is_authed(token)
    spec = await field_spec_controller.get(id=id)
    spec_dict = await spec.to_dict()
    return Success(data=spec_dict)


@router.post("/field_spec/create", summary="创建字段明细")
async def create_field_spec(spec_in: FieldSpecCreate, token: str = Header(...)):
    current_user = await AuthControl.is_authed(token)

    success, msg, effective_tenant_id = TenantControl.validate_create_tenant_id(
        current_user, spec_in.tenant_id
    )
    if not success:
        return Fail(code=400, msg=msg)

    spec = await field_spec_controller.create_field_spec(obj_in=spec_in, tenant_id=effective_tenant_id, app_name=spec_in.app_name)
    spec_dict = await spec.to_dict()
    return Success(data=spec_dict)


@router.post("/field_spec/update", summary="更新字段明细")
async def update_field_spec(spec_in: FieldSpecUpdate, token: str = Header(...)):
    await AuthControl.is_authed(token)
    spec = await field_spec_controller.get(id=spec_in.id)

    if not TenantContext.is_superuser() and spec.tenant_id != TenantContext.get_tenant_id():
        return Fail(code=403, msg="无权操作其他租户的字段")

    updated = await field_spec_controller.update_field_spec(id=spec_in.id, obj_in=spec_in, tenant_id=spec.tenant_id, app_name=spec.app_name)
    spec_dict = await updated.to_dict()
    return Success(data=spec_dict)


@router.delete("/field_spec/delete", summary="删除字段明细")
async def delete_field_spec(id: int = Query(...), token: str = Header(...)):
    current_user = await AuthControl.is_authed(token)
    spec = await field_spec_controller.get(id=id)

    success, msg = TenantControl.validate_delete_permission(
        current_user, spec.tenant_id
    )
    if not success:
        return Fail(code=403, msg=msg)

    await field_spec_controller.delete_field_spec(id=id)
    return Success(msg="删除成功")


class BatchDeleteFieldSpecsRequest(BaseModel):
    ids: List[int]


@router.post("/field_spec/batch_delete", summary="批量删除字段明细")
async def batch_delete_field_specs(
    request: BatchDeleteFieldSpecsRequest,
    token: str = Header(...)
):
    """批量删除字段明细"""
    current_user = await AuthControl.is_authed(token)

    if not request.ids:
        return Fail(code=400, msg="请选择要删除的字段")

    deleted_count = 0
    failed_count = 0
    failed_ids = []

    for field_id in request.ids:
        try:
            spec = await field_spec_controller.get(id=field_id)
            if not spec:
                failed_count += 1
                failed_ids.append(field_id)
                continue

            success, msg = TenantControl.validate_delete_permission(
                current_user, spec.tenant_id
            )
            if not success:
                failed_count += 1
                failed_ids.append(field_id)
                continue

            await field_spec_controller.delete_field_spec(id=field_id)
            deleted_count += 1
        except Exception as e:
            failed_count += 1
            failed_ids.append(field_id)

    return Success(data={
        "deleted_count": deleted_count,
        "failed_count": failed_count,
        "failed_ids": failed_ids
    }, msg=f"成功删除 {deleted_count} 个字段")


@router.get("/field_spec/by_group", summary="获取字段组下的所有字段")
async def get_field_specs_by_group(field_group_id: int = Query(...), token: str = Header(...)):
    await AuthControl.is_authed(token)
    group = await field_group_config_controller.get(id=field_group_id)
    if not group:
        return Fail(code=400, msg="字段组不存在")

    if not TenantContext.is_superuser() and group.tenant_id != TenantContext.get_tenant_id():
        return Fail(code=403, msg="无权查看其他租户的字段")

    fields = await field_spec_controller.get_by_field_group(field_group_id)
    data = [await obj.to_dict() for obj in fields]
    return Success(data=data)


@router.get("/field_spec/by_app", summary="获取应用下的所有字段")
async def get_field_specs_by_app(app_name: str = Query(...), token: str = Header(...)):
    """获取指定应用下的所有字段（用于关联字段选择）"""
    await AuthControl.is_authed(token)

    # 构建查询条件
    q = Q(app_name=app_name)

    # 如果不是超级管理员，只能查看当前租户的字段
    if not TenantContext.is_superuser():
        q &= Q(tenant_id=TenantContext.get_tenant_id())

    # 查询字段
    fields = await FieldSpec.filter(q).all()
    data = [await obj.to_dict() for obj in fields]
    return Success(data=data)


class BatchAddFieldsRequest(BaseModel):
    field_group_id: int
    field_spec_ids: List[int]


@router.post("/field_group/batch_add_fields", summary="批量添加字段到字段组")
async def batch_add_fields_to_group(
    data: BatchAddFieldsRequest,
    token: str = Header(...)
):
    """批量添加字段到字段组"""
    await AuthControl.is_authed(token)

    field_group_id = data.field_group_id
    field_spec_ids = data.field_spec_ids

    group = await field_group_config_controller.get(id=field_group_id)
    if not group:
        return Fail(code=400, msg="字段组不存在")

    if not TenantContext.is_superuser() and group.tenant_id != TenantContext.get_tenant_id():
        return Fail(code=403, msg="无权操作其他租户的字段组")

    success_count = 0
    failed_count = 0

    for field_spec_id in field_spec_ids:
        field = await field_spec_controller.get(id=field_spec_id)
        if not field:
            failed_count += 1
            continue

        if field.tenant_id != group.tenant_id:
            failed_count += 1
            continue

        existing = await FieldGroupFieldSpec.filter(
            field_group_id=field_group_id,
            field_spec_id=field_spec_id
        ).first()
        if existing:
            success_count += 1
            continue

        await FieldGroupFieldSpec.create(
            field_group_id=field_group_id,
            field_spec_id=field_spec_id,
            tenant_id=group.tenant_id,
            app_name=group.app_name
        )
        success_count += 1

    return Success(data={
        "success_count": success_count,
        "failed_count": failed_count,
        "message": f"批量添加完成，成功 {success_count} 个，失败 {failed_count} 个"
    })


class BatchRemoveFieldsRequest(BaseModel):
    field_group_id: int
    field_spec_ids: List[int]


@router.post("/field_group/batch_remove_fields", summary="批量从字段组移除字段")
async def batch_remove_fields_from_group(
    data: BatchRemoveFieldsRequest,
    token: str = Header(...)
):
    """批量从字段组移除字段关联"""
    await AuthControl.is_authed(token)

    field_group_id = data.field_group_id
    field_spec_ids = data.field_spec_ids

    group = await FieldGroupConfig.filter(id=field_group_id).first()
    if not group:
        return Fail(code=404, msg="字段组不存在")

    removed_count = 0
    failed_count = 0

    for field_spec_id in field_spec_ids:
        existing = await FieldGroupFieldSpec.filter(
            field_group_id=field_group_id,
            field_spec_id=field_spec_id
        ).first()
        if existing:
            await existing.delete()
            removed_count += 1
        else:
            failed_count += 1

    return Success(data={
        "removed_count": removed_count,
        "failed_count": failed_count,
        "message": f"批量移除完成，成功移除 {removed_count} 个，失败 {failed_count} 个"
    })
