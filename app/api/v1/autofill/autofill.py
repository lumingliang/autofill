import csv
import io
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Body, Header, Query, Request, UploadFile, File
from tortoise.expressions import Q

from app.controllers.autofill import (app_management_controller,
                                      dropdown_option_controller,
                                      fill_data_record_controller,
                                      summary_template_controller)
from app.core.autofill_auth import APIKeyAuth
from app.core.dependency import AuthControl, is_superuser, build_tenant_query, get_effective_tenant_id
from app.schemas.base import Fail, Success, SuccessExtra
from app.models.admin import Tenant, User
from app.schemas.autofill import *

logger = logging.getLogger(__name__)

# 创建多个 router，分别对应不同的功能模块
app_router = APIRouter()
template_router = APIRouter()
dropdown_router = APIRouter()
record_router = APIRouter()


# ==================== 应用管理接口 ====================

@app_router.get("/app/list", summary="应用列表")
async def list_app(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    app_name: str = Query("", description="应用名称"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    q = Q()
    if app_name:
        q &= Q(app_name__contains=app_name)

    # 多租户筛选
    tenant_query = build_tenant_query(current_user, tenant_id)
    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])

    total, apps = await app_management_controller.list(
        page=page, page_size=page_size, search=q, order=["-updated_at"]
    )
    data = [await obj.to_dict() for obj in apps]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@app_router.get("/app/get", summary="应用详情")
async def get_app(
    id: int = Query(..., description="应用ID"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    app = await app_management_controller.get(id=id)
    return Success(data=await app.to_dict())


@app_router.post("/app/create", summary="创建应用")
async def create_app(
    app_in: AppCreate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    # 确定租户ID
    if is_superuser(current_user):
        target_tenant_id = app_in.tenant_id if app_in.tenant_id > 0 else 0
    else:
        target_tenant_id = current_user.current_tenant_id
        if target_tenant_id <= 0:
            return Fail(code=400, msg="您当前未选择租户，无法创建应用")

    # 使用确定的租户ID
    app_in.tenant_id = target_tenant_id
    app = await app_management_controller.create_app(obj_in=app_in)
    return Success(data=await app.to_dict())


@app_router.post("/app/update", summary="更新应用")
async def update_app(
    app_in: AppUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    app = await app_management_controller.get(id=app_in.id)

    # 权限检查
    if not is_superuser(current_user):
        if app.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的应用")

    updated = await app_management_controller.update_app(id=app_in.id, obj_in=app_in)
    return Success(data=await updated.to_dict())


@app_router.delete("/app/delete", summary="删除应用")
async def delete_app(
    id: int = Query(..., description="应用ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    app = await app_management_controller.get(id=id)

    # 权限检查
    if not is_superuser(current_user):
        if app.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的应用")

    await app_management_controller.remove(id=id)
    return Success(msg="删除成功")


@app_router.get("/app/select", summary="应用名称下拉列表")
async def get_app_select(
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """
    获取应用名称下拉列表，供其他模块使用
    """
    current_user = await AuthControl.is_authed(token)

    q = Q(is_active=True)

    # 多租户筛选
    tenant_query = build_tenant_query(current_user, tenant_id)
    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])

    apps = await app_management_controller.model.filter(q).all()
    data = [{"label": app.app_name, "value": app.app_name} for app in apps]
    return Success(data=data)


# ==================== 总结模板管理接口 ====================

@template_router.get("/template/list", summary="模板列表")
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

    # 多租户筛选
    tenant_query = build_tenant_query(current_user, tenant_id)
    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])

    total, templates = await summary_template_controller.list(
        page=page, page_size=page_size, search=q, order=["-updated_at"]
    )
    data = [await obj.to_dict() for obj in templates]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@template_router.get("/template/get", summary="模板详情")
async def get_template(
    id: int = Query(..., description="模板ID"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    template = await summary_template_controller.get(id=id)
    return Success(data=await template.to_dict())


@template_router.post("/template/create", summary="创建模板")
async def create_template(
    template_in: SummaryTemplateCreate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    # 确定租户ID
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


@template_router.post("/template/update", summary="更新模板")
async def update_template(
    template_in: SummaryTemplateUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    template = await summary_template_controller.get(id=template_in.id)

    # 权限检查
    if not is_superuser(current_user):
        if template.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的模板")

    updated = await summary_template_controller.update_template(id=template_in.id, obj_in=template_in)
    return Success(data=await updated.to_dict())


@template_router.delete("/template/delete", summary="删除模板")
async def delete_template(
    id: int = Query(..., description="模板ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    template = await summary_template_controller.get(id=id)

    # 权限检查
    if not is_superuser(current_user):
        if template.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的模板")

    await summary_template_controller.remove(id=id)
    return Success(msg="删除成功")


@template_router.post("/template/import", summary="CSV批量导入总结模板")
async def import_template_from_csv(
    file: UploadFile = File(..., description="CSV文件"),
    app_name: str = Query(..., description="应用名称"),
    tenant_id: int = Query(None, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """
    CSV格式: name,class_name,summary,template_content
    示例:
    预约充电故障,充电故障,车主反馈预约充电功能异常，需排查充电设置及系统问题,车主X先生反馈：...
    """
    current_user = await AuthControl.is_authed(token)

    # 确定租户ID
    target_tenant_id = tenant_id
    if is_superuser(current_user):
        if target_tenant_id <= 0:
            return Fail(code=400, msg="请指定租户ID")
    else:
        target_tenant_id = current_user.current_tenant_id
        if target_tenant_id <= 0:
            return Fail(code=400, msg="您当前未选择租户")

    # 检查文件类型
    if not file.filename.endswith('.csv'):
        return Fail(code=400, msg="请上传CSV文件")

    try:
        # 读取CSV内容
        content = await file.read()
        content_str = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content_str))

        # 验证必填字段
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

        for idx, row in enumerate(rows, start=2):  # 从第2行开始（第1行是表头）
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

                # 检查是否已存在（同一租户+应用+分类+名称）
                existing = await summary_template_controller.model.filter(
                    tenant_id=target_tenant_id,
                    app_name=app_name,
                    class_name=class_name,
                    name=name
                ).first()

                if existing:
                    # 更新现有模板
                    existing.summary = summary
                    existing.template_content = template_content
                    await existing.save()
                    updated_count += 1
                else:
                    # 创建新模板
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


# ==================== 下拉选项管理接口 ====================

@dropdown_router.get("/dropdown/list", summary="下拉选项列表")
async def list_dropdown(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    app_name: str = Query("", description="应用名称"),
    class_name: str = Query("", description="分类名称"),
    parent_id: int = Query(0, description="父选项ID"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    q = Q()
    if app_name:
        q &= Q(app_name__contains=app_name)
    if class_name:
        q &= Q(class_name__contains=class_name)
    if parent_id >= 0:
        q &= Q(parent_id=parent_id)

    # 多租户筛选
    tenant_query = build_tenant_query(current_user, tenant_id)
    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])

    total, options = await dropdown_option_controller.list(
        page=page, page_size=page_size, search=q, order=["-updated_at"]
    )
    data = [await obj.to_dict() for obj in options]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@dropdown_router.get("/dropdown/tree", summary="下拉选项树形结构")
async def get_dropdown_tree(
    app_name: str = Query(..., description="应用名称"),
    parent_id: int = Query(0, description="父选项ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    tenant_id = current_user.current_tenant_id
    if tenant_id <= 0 and is_superuser(current_user):
        # 超级管理员需要指定租户
        return Fail(code=400, msg="请指定租户ID")

    tree = await dropdown_option_controller.get_tree(tenant_id, app_name, parent_id)
    return Success(data=tree)


@dropdown_router.get("/dropdown/get", summary="下拉选项详情")
async def get_dropdown(
    id: int = Query(..., description="选项ID"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    option = await dropdown_option_controller.get(id=id)
    data = await option.to_dict()

    # 查询子选项
    children = await dropdown_option_controller.model.filter(parent_id=id).all()
    data["children"] = [await child.to_dict() for child in children]

    return Success(data=data)


@dropdown_router.post("/dropdown/create", summary="创建下拉选项")
async def create_dropdown(
    option_in: DropdownOptionCreate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    # 确定租户ID
    target_tenant_id = 0
    if is_superuser(current_user):
        target_tenant_id = option_in.tenant_id
    else:
        target_tenant_id = current_user.current_tenant_id
        if target_tenant_id <= 0:
            return Fail(code=400, msg="您当前未选择租户，无法创建选项")

    option_in.tenant_id = target_tenant_id
    option = await dropdown_option_controller.create_option(obj_in=option_in)
    return Success(data=await option.to_dict())


@dropdown_router.post("/dropdown/update", summary="更新下拉选项")
async def update_dropdown(
    option_in: DropdownOptionUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    option = await dropdown_option_controller.get(id=option_in.id)

    # 权限检查
    if not is_superuser(current_user):
        if option.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的选项")

    updated = await dropdown_option_controller.update_option(id=option_in.id, obj_in=option_in)
    return Success(data=await updated.to_dict())


@dropdown_router.delete("/dropdown/delete", summary="删除下拉选项")
async def delete_dropdown(
    id: int = Query(..., description="选项ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    option = await dropdown_option_controller.get(id=id)

    # 权限检查
    if not is_superuser(current_user):
        if option.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的选项")

    # 检查是否有子选项
    children_count = await dropdown_option_controller.model.filter(parent_id=id).count()
    if children_count > 0:
        return Fail(code=400, msg="该选项下有子选项，请先删除子选项")

    await dropdown_option_controller.remove(id=id)
    return Success(msg="删除成功")


@dropdown_router.post("/dropdown/import", summary="CSV批量导入下拉选项")
async def import_dropdown_from_csv(
    file: UploadFile = File(..., description="CSV文件"),
    app_name: str = Query(..., description="应用名称"),
    tenant_id: int = Query(None, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """
    CSV格式: option_value,summary,class_name,parent_option_value
    示例:
    产品咨询,客户询问车辆配置等相关信息,业务类型,
    4S店,客户询问车辆配置等相关信息,业务类型,
    """
    current_user = await AuthControl.is_authed(token)

    # 确定租户ID
    target_tenant_id = tenant_id
    if is_superuser(current_user):
        if target_tenant_id <= 0:
            return Fail(code=400, msg="请指定租户ID")
    else:
        target_tenant_id = current_user.current_tenant_id
        if target_tenant_id <= 0:
            return Fail(code=400, msg="您当前未选择租户")

    # 检查文件类型
    if not file.filename.endswith('.csv'):
        return Fail(code=400, msg="请上传CSV文件")

    try:
        # 读取CSV内容
        content = await file.read()
        content_str = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content_str))

        # 验证必填字段
        required_fields = ['option_value', 'class_name']
        if not csv_reader.fieldnames:
            return Fail(code=400, msg="CSV文件格式错误：无法读取表头")

        for field in required_fields:
            if field not in csv_reader.fieldnames:
                return Fail(code=400, msg=f"CSV文件缺少必填字段: {field}")

        # 先读取所有行，建立选项值到ID的映射（用于处理父子关系）
        rows = list(csv_reader)
        created_count = 0
        updated_count = 0
        errors = []

        # 第一遍：创建/更新所有选项（parent_id先设为0）
        value_to_id = {}  # 记录本次导入创建的选项值到ID的映射

        for idx, row in enumerate(rows, start=2):  # 从第2行开始（第1行是表头）
            try:
                option_value = row.get('option_value', '').strip()
                class_name = row.get('class_name', '').strip()

                if not option_value:
                    errors.append(f"第{idx}行: 选项值不能为空")
                    continue

                if not class_name:
                    errors.append(f"第{idx}行: 分类名称不能为空")
                    continue

                summary = row.get('summary', '').strip()
                parent_option_value = row.get('parent_option_value', '').strip()

                # 检查是否已存在
                existing = await dropdown_option_controller.model.filter(
                    tenant_id=target_tenant_id,
                    app_name=app_name,
                    class_name=class_name,
                    option_value=option_value
                ).first()

                if existing:
                    # 更新现有选项
                    existing.summary = summary
                    existing.parent_id = 0  # 先设为0，第二遍再更新
                    await existing.save()
                    value_to_id[option_value] = existing.id
                    updated_count += 1
                else:
                    # 创建新选项
                    option = await dropdown_option_controller.model.create(
                        tenant_id=target_tenant_id,
                        app_name=app_name,
                        class_name=class_name,
                        option_value=option_value,
                        summary=summary,
                        parent_id=0,
                        description=''
                    )
                    value_to_id[option_value] = option.id
                    created_count += 1

            except Exception as e:
                errors.append(f"第{idx}行: {str(e)}")

        # 第二遍：更新父子关系
        for idx, row in enumerate(rows, start=2):
            try:
                option_value = row.get('option_value', '').strip()
                parent_option_value = row.get('parent_option_value', '').strip()

                if not option_value or not parent_option_value:
                    continue

                # 查找当前选项
                option = await dropdown_option_controller.model.filter(
                    tenant_id=target_tenant_id,
                    app_name=app_name,
                    option_value=option_value
                ).first()

                if option and parent_option_value in value_to_id:
                    option.parent_id = value_to_id[parent_option_value]
                    await option.save()
                elif option:
                    # 父选项不在本次导入中，尝试从数据库查找
                    parent = await dropdown_option_controller.model.filter(
                        tenant_id=target_tenant_id,
                        app_name=app_name,
                        option_value=parent_option_value
                    ).first()
                    if parent:
                        option.parent_id = parent.id
                        await option.save()

            except Exception as e:
                errors.append(f"第{idx}行更新父子关系失败: {str(e)}")

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


# ==================== 填单记录管理接口 ====================

@record_router.get("/record/list", summary="填单记录列表")
async def list_record(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    session_id: str = Query("", description="会话ID"),
    phone: str = Query("", description="手机号"),
    user_unique_id: str = Query("", description="用户唯一标识"),
    app_name: str = Query("", description="应用名称"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    q = Q()
    if session_id:
        q &= Q(session_id__contains=session_id)
    if phone:
        q &= Q(phone__contains=phone)
    if user_unique_id:
        q &= Q(user_unique_id__contains=user_unique_id)
    if app_name:
        q &= Q(app_name__contains=app_name)

    # 多租户筛选
    tenant_query = build_tenant_query(current_user, tenant_id)
    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])

    total, records = await fill_data_record_controller.list(
        page=page, page_size=page_size, search=q, order=["-updated_at"]
    )
    data = [await obj.to_dict() for obj in records]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@record_router.get("/record/get", summary="填单记录详情")
async def get_record(
    id: int = Query(..., description="记录ID"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    record = await fill_data_record_controller.get(id=id)
    return Success(data=await record.to_dict())


@record_router.post("/record/update", summary="更新填单记录")
async def update_record(
    record_in: FillDataRecordUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    record = await fill_data_record_controller.get(id=record_in.id)

    # 权限检查
    if not is_superuser(current_user):
        if record.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的记录")

    updated = await fill_data_record_controller.update(id=record_in.id, obj_in=record_in)
    return Success(data=await updated.to_dict())


@record_router.delete("/record/delete", summary="删除填单记录")
async def delete_record(
    id: int = Query(..., description="记录ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    record = await fill_data_record_controller.get(id=id)

    # 权限检查
    if not is_superuser(current_user):
        if record.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的记录")

    await fill_data_record_controller.remove(id=id)
    return Success(msg="删除成功")
