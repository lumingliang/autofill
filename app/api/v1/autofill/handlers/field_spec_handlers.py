"""
字段明细管理接口
"""
import csv
import io
from datetime import datetime
from typing import List

from fastapi import APIRouter, File, Header, Query, UploadFile
from pydantic import BaseModel
from tortoise.expressions import Q

from app.controllers.autofill import (
    field_group_config_controller,
    field_spec_controller,
)
from app.core.dependency import AuthControl, is_superuser, build_tenant_query
from app.models.autofill import FieldGroupFieldSpec
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.fill_page import FieldSpecCreate, FieldSpecUpdate, SwaggerSyncRequest
from app.services.agent_v2.openapi_parser import OpenAPIParser

router = APIRouter()


@router.get("/field_spec/list", summary="字段明细列表")
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
    tenant_query = build_tenant_query(current_user, tenant_id)

    if field_group_id > 0:
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

    data = []
    for spec in specs:
        spec_dict = await spec.to_dict()
        relations = await FieldGroupFieldSpec.filter(field_spec_id=spec.id).all()
        group_ids = [r.field_group_id for r in relations]
        spec_dict['field_group_ids'] = group_ids
        groups = await field_group_config_controller.model.filter(id__in=group_ids).all()
        spec_dict['field_groups'] = [
            {"id": g.id, "group_name": g.group_name, "group_code": g.group_code}
            for g in groups
        ]
        data.append(spec_dict)

    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/field_spec/get", summary="字段明细详情")
async def get_field_spec(
    id: int = Query(..., description="字段明细ID"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    spec = await field_spec_controller.get(id=id)
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


@router.post("/field_spec/create", summary="创建字段明细")
async def create_field_spec(
    spec_in: FieldSpecCreate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

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

    if is_superuser(current_user):
        target_tenant_id = spec_in.tenant_id if spec_in.tenant_id > 0 else first_group.tenant_id
        target_app_name = spec_in.app_name if spec_in.app_name else first_group.app_name
    else:
        target_tenant_id = first_group.tenant_id
        target_app_name = first_group.app_name
        if current_user.current_tenant_id > 0 and first_group.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权在该字段组下创建字段")

    spec = await field_spec_controller.create_field_spec(
        obj_in=spec_in,
        tenant_id=target_tenant_id,
        app_name=target_app_name
    )

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


@router.post("/field_spec/update", summary="更新字段明细")
async def update_field_spec(
    spec_in: FieldSpecUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    spec = await field_spec_controller.get(id=spec_in.id)

    if not is_superuser(current_user):
        if spec.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的字段")

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


@router.delete("/field_spec/delete", summary="删除字段明细")
async def delete_field_spec(
    id: int = Query(..., description="字段明细ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    spec = await field_spec_controller.get(id=id)

    if not is_superuser(current_user):
        if spec.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的字段")

    await field_spec_controller.remove(id=id)
    return Success(msg="删除成功")


@router.get("/field_spec/by_group", summary="获取字段组下的所有字段")
async def get_field_specs_by_group(
    field_group_id: int = Query(..., description="字段组ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    group = await field_group_config_controller.get(id=field_group_id)
    if not group:
        return Fail(code=400, msg="字段组不存在")

    if not is_superuser(current_user):
        if group.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权查看其他租户的字段")

    fields = await field_spec_controller.get_by_field_group(field_group_id)
    data = [await obj.to_dict() for obj in fields]
    return Success(data=data)


@router.post("/field_spec/sync_swagger", summary="同步 Swagger 文档并解析为选项")
async def sync_swagger_document(
    sync_in: SwaggerSyncRequest,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    spec = await field_spec_controller.get(id=sync_in.field_spec_id)
    if not spec:
        return Fail(code=404, msg="字段明细不存在")

    group = await field_group_config_controller.get(id=spec.field_group_id)
    if not group:
        return Fail(code=400, msg="字段组不存在")

    if not is_superuser(current_user):
        if group.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的字段")

    if spec.field_type != "select":
        return Fail(code=400, msg="只有下拉选择类型的字段才支持 Swagger 同步")

    try:
        parser = OpenAPIParser(sync_in.swagger_json)
        endpoints = parser.get_endpoints()

        if not endpoints:
            return Fail(code=400, msg="未能从 Swagger 文档中解析出任何 API 端点")

        option_items = []
        for endpoint in endpoints:
            value = endpoint.operation_id or f"{endpoint.method}_{endpoint.path.replace('/', '_')}"
            label = endpoint.summary or endpoint.description or f"{endpoint.method.upper()} {endpoint.path}"
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

        current_options = spec.options or {}
        current_options["source"] = "api"
        current_options["items"] = option_items
        current_options["swagger_json"] = sync_in.swagger_json
        current_options["appkey"] = sync_in.appkey
        current_options["last_sync_at"] = datetime.now().isoformat()
        current_options["sync_endpoints_count"] = len(endpoints)

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


class ExportRequest(BaseModel):
    """导出请求"""
    ids: List[int]


@router.post("/field_spec/export", summary="导出字段明细")
async def export_field_specs(
    export_in: ExportRequest,
    token: str = Header(..., description="token验证"),
):
    """
    导出字段明细为两个CSV文件：
    1. 基础字段信息（ID, 字段名, 字段标签, 字段类型, 填写指引, corrections）
    2. 选项详情（针对select类型字段的选项信息）
    """
    current_user = await AuthControl.is_authed(token)

    # 构建查询条件 - 超级管理员可以导出任何字段，普通用户只能导出自己租户的字段
    query = Q(id__in=export_in.ids)
    if not is_superuser(current_user):
        query &= Q(tenant_id=current_user.current_tenant_id)

    # 查询选中的字段
    specs = await field_spec_controller.model.filter(query).all()

    if not specs:
        return Fail(code=404, msg="未找到要导出的字段")

    # 准备基础字段CSV
    base_output = io.StringIO()
    base_writer = csv.writer(base_output)
    base_writer.writerow(['ID', '字段名', '字段标签', '字段类型', '填写指引', 'corrections'])

    # 准备选项详情CSV
    options_output = io.StringIO()
    options_writer = csv.writer(options_output)
    options_writer.writerow(['字段ID', '字段名', '选项值', '选项标签', '填写说明', 'corrections'])

    for spec in specs:
        # 写入基础字段信息
        corrections_text = ''
        if spec.corrections:
            # 每行都以 * 开头
            corrections_text = '\n'.join(['*' + c.get('text', '') for c in spec.corrections if c.get('text')])

        base_writer.writerow([
            spec.id,
            spec.field_name,
            spec.field_label or '',
            spec.field_type.value if spec.field_type else '',
            spec.fill_instruction or '',
            corrections_text
        ])

        # 写入选项详情（仅select类型）
        if spec.field_type == 'select' and spec.options:
            items = spec.options.get('items', [])
            for item in items:
                if item.get('is_deleted'):
                    continue

                # 处理选项的corrections
                option_corrections = item.get('corrections', '')
                if isinstance(option_corrections, list):
                    # 每行都以 * 开头
                    option_corrections = '\n'.join(['*' + c.get('text', '') for c in option_corrections if c.get('text')])

                options_writer.writerow([
                    spec.id,
                    spec.field_name,
                    item.get('value', ''),
                    item.get('label', ''),
                    item.get('fill_instruction', ''),
                    option_corrections
                ])

    return Success(data={
        "base_csv": base_output.getvalue(),
        "options_csv": options_output.getvalue()
    })


@router.post("/field_spec/import", summary="导入字段明细")
async def import_field_specs(
    file: UploadFile = File(..., description="CSV文件"),
    token: str = Header(..., description="token验证"),
):
    """
    从CSV文件导入字段明细
    支持两种CSV格式：
    1. 基础字段信息（ID, 字段名, 字段标签, 字段类型, 填写指引, corrections）
    2. 选项详情（字段ID, 字段名, 选项值, 选项标签, 填写说明, corrections）
    """
    current_user = await AuthControl.is_authed(token)
    tenant_id = current_user.current_tenant_id if not is_superuser(current_user) else 0
    app_name = "autofill"  # 默认应用名

    if not file.filename.endswith('.csv'):
        return Fail(code=400, msg="请上传CSV文件")

    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content_str))

        # 检测CSV类型
        fieldnames = csv_reader.fieldnames or []
        is_options_csv = '字段ID' in fieldnames and '选项值' in fieldnames

        success_count = 0
        error_messages = []

        if is_options_csv:
            # 处理选项详情CSV
            for row in csv_reader:
                try:
                    field_id = row.get('字段ID', '').strip()
                    field_name = row.get('字段名', '').strip()
                    option_value = row.get('选项值', '').strip()
                    option_label = row.get('选项标签', '').strip()
                    fill_instruction = row.get('填写说明', '').strip()
                    corrections_text = row.get('corrections', '').strip()

                    if not field_id or not option_value:
                        error_messages.append(f"跳过缺少字段ID或选项值的行")
                        continue

                    # 查找字段
                    existing_query = Q(id=int(field_id))
                    if not is_superuser(current_user):
                        existing_query &= Q(tenant_id=tenant_id)
                    existing = await field_spec_controller.model.filter(existing_query).first()

                    if not existing:
                        error_messages.append(f"字段ID {field_id} 不存在或无权限，跳过")
                        continue

                    # 解析corrections - 每行以 * 开头
                    corrections = []
                    if corrections_text:
                        for line in corrections_text.split('\n'):
                            line = line.strip()
                            if line.startswith('*'):
                                text = line[1:].strip()  # 去掉开头的 *
                                if text:
                                    corrections.append({"text": text})

                    # 更新选项
                    options = existing.options or {}
                    items = options.get('items', [])

                    # 查找并更新选项
                    option_found = False
                    for item in items:
                        if str(item.get('value', '')) == option_value:
                            item['label'] = option_label
                            item['fill_instruction'] = fill_instruction
                            item['corrections'] = corrections
                            option_found = True
                            break

                    if not option_found:
                        # 添加新选项
                        items.append({
                            'value': option_value,
                            'label': option_label,
                            'fill_instruction': fill_instruction,
                            'corrections': corrections,
                            'is_deleted': False
                        })

                    options['items'] = items
                    existing.options = options
                    await existing.save()
                    success_count += 1

                except Exception as e:
                    error_messages.append(f"处理行失败: {str(e)}")
        else:
            # 处理基础字段信息CSV
            for row in csv_reader:
                try:
                    field_id = row.get('ID', '').strip()
                    field_name = row.get('字段名', '').strip()
                    field_label = row.get('字段标签', '').strip()
                    field_type = row.get('字段类型', '').strip()
                    fill_instruction = row.get('填写指引', '').strip()
                    corrections_text = row.get('corrections', '').strip()

                    if not field_name:
                        error_messages.append(f"跳过空字段名行")
                        continue

                    # 解析corrections - 每行以 * 开头
                    corrections = []
                    if corrections_text:
                        for line in corrections_text.split('\n'):
                            line = line.strip()
                            if line.startswith('*'):
                                text = line[1:].strip()  # 去掉开头的 *
                                if text:
                                    corrections.append({"text": text})

                    # 准备数据
                    data = {
                        "field_name": field_name,
                        "field_label": field_label,
                        "field_type": field_type,
                        "fill_instruction": fill_instruction,
                        "corrections": corrections,
                        "is_active": True,
                    }

                    if field_id:
                        # 更新已有字段 - 超级管理员可以更新任何字段，普通用户只能更新自己租户的字段
                        existing_query = Q(id=int(field_id))
                        if not is_superuser(current_user):
                            existing_query &= Q(tenant_id=tenant_id)
                        existing = await field_spec_controller.model.filter(existing_query).first()
                        if existing:
                            await field_spec_controller.update(id=int(field_id), obj_in=data)
                            success_count += 1
                        else:
                            error_messages.append(f"字段ID {field_id} 不存在或无权限，跳过")
                    else:
                        # 检查字段名是否已存在（仅检查当前租户）
                        existing_query = Q(field_name=field_name)
                        if not is_superuser(current_user):
                            existing_query &= Q(tenant_id=tenant_id)
                        existing = await field_spec_controller.model.filter(existing_query).first()
                        if existing:
                            error_messages.append(f"字段名 {field_name} 已存在，跳过")
                            continue

                        # 创建新字段
                        data["tenant_id"] = tenant_id if tenant_id > 0 else 0
                        data["app_name"] = app_name
                        await field_spec_controller.create(obj_in=data)
                        success_count += 1

                except Exception as e:
                    error_messages.append(f"处理行失败: {str(e)}")

        result = {
            "success_count": success_count,
            "errors": error_messages[:10]  # 最多返回10条错误
        }

        if error_messages:
            result["error_count"] = len(error_messages)

        return Success(data=result)

    except Exception as e:
        return Fail(code=500, msg=f"导入失败: {str(e)}")
