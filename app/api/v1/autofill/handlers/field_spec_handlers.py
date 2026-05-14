"""
字段明细管理接口
"""
import csv
import io
import json
import os
import tempfile
from datetime import datetime
from typing import List, Dict, Any

import httpx
import prance
import yaml
from fastapi import APIRouter, File, Header, Query, UploadFile
from jsonpath_ng import parse as jsonpath_parse
from pydantic import BaseModel
from tortoise.expressions import Q

from app.controllers.autofill import field_group_config_controller, field_spec_controller
from app.core.dependency import AuthControl, TenantControl
from app.core.tenant import TenantContext
from app.models.admin import Tenant
from app.models.autofill import FieldGroupFieldSpec, FieldGroupConfig, FillPage
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.fill_page import (
    FieldSpecCreate, FieldSpecUpdate, FieldSpecSyncOptionsRequest,
    CurlParseRequest
)
from app.services.autofill.field_spec_service import upsert_field_spec
from app.services.autofill.field_flatten_service import FieldFlattener
from app.utils.curl_parser import parse_curl_command, generate_openapi_schema_from_curl

router = APIRouter()


def parse_openapi_schema(schema_content: str) -> Dict[str, Any]:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(schema_content)
        temp_path = f.name
    try:
        parser = prance.ResolvingParser(temp_path, backend='openapi-spec-validator')
        return parser.specification
    finally:
        os.unlink(temp_path)


def get_endpoint_config(spec: Dict[str, Any]) -> tuple:
    servers = spec.get('servers', [])
    base_url = servers[0].get('url', '') if servers else ''
    paths = spec.get('paths', {})
    if not paths:
        raise ValueError("Schema中未找到paths配置")
    for path, methods in paths.items():
        if 'get' in methods:
            return base_url, path, 'get', methods['get']
        if 'post' in methods:
            return base_url, path, 'post', methods['post']
    raise ValueError("Schema中未找到GET或POST接口")


@router.get("/field_spec/list", summary="字段明细列表")
async def list_field_spec(
    page: int = Query(1),
    page_size: int = Query(10),
    field_name: str = Query(""),
    field_label: str = Query(""),
    field_type: str = Query(""),
    field_group_id: int = Query(0),
    tenant_id: int = Query(0),
    token: str = Header(...),
):
    await AuthControl.is_authed(token)
    tenant_filter = TenantContext.build_query_filter(tenant_id)

    if field_group_id > 0:
        relation_q = Q(field_group_id=field_group_id)
        if tenant_filter:
            relation_q &= Q(**tenant_filter)
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
    if tenant_filter:
        q &= Q(**tenant_filter)

    total, specs = await field_spec_controller.list(page=page, page_size=page_size, search=q, order=["-updated_at"])

    data = []
    for spec in specs:
        spec_dict = await spec.to_dict()
        relations = await FieldGroupFieldSpec.filter(field_spec_id=spec.id).all()
        group_ids = [r.field_group_id for r in relations]
        spec_dict['field_group_ids'] = group_ids
        groups = await field_group_config_controller.model.filter(id__in=group_ids).all()
        spec_dict['field_groups'] = [{"id": g.id, "group_name": g.group_name, "group_code": g.group_code} for g in groups]
        data.append(spec_dict)

    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/field_spec/get", summary="字段明细详情")
async def get_field_spec(id: int = Query(...), token: str = Header(...)):
    await AuthControl.is_authed(token)
    spec = await field_spec_controller.get(id=id)
    spec_dict = await spec.to_dict()
    relations = await FieldGroupFieldSpec.filter(field_spec_id=spec.id).all()
    group_ids = [r.field_group_id for r in relations]
    spec_dict['field_group_ids'] = group_ids
    groups = await field_group_config_controller.model.filter(id__in=group_ids).all()
    spec_dict['field_groups'] = [{"id": g.id, "group_name": g.group_name, "group_code": g.group_code} for g in groups]
    return Success(data=spec_dict)


@router.post("/field_spec/create", summary="创建字段明细")
async def create_field_spec(spec_in: FieldSpecCreate, token: str = Header(...)):
    current_user = await AuthControl.is_authed(token)

    if not spec_in.field_group_ids:
        return Fail(code=400, msg="必须至少选择一个字段组")

    first_group = None
    for group_id in spec_in.field_group_ids:
        group = await field_group_config_controller.get(id=group_id)
        if not group:
            return Fail(code=400, msg=f"字段组(ID:{group_id})不存在")
        if not TenantContext.is_superuser() and group.tenant_id != TenantContext.get_tenant_id():
            return Fail(code=403, msg=f"无权操作字段组(ID:{group_id})")
        if not first_group:
            first_group = group

    # 使用公共方法验证租户ID
    success, msg, effective_tenant_id = TenantControl.validate_create_tenant_id(
        current_user, spec_in.tenant_id
    )
    if not success:
        return Fail(code=400, msg=msg)
    
    # 如果超管没传tenant_id，使用第一个字段组的租户
    if TenantContext.is_superuser() and spec_in.tenant_id <= 0:
        effective_tenant_id = first_group.tenant_id
    
    target_tenant_id = effective_tenant_id
    target_app_name = spec_in.app_name if spec_in.app_name else first_group.app_name

    spec = await field_spec_controller.create_field_spec(obj_in=spec_in, tenant_id=target_tenant_id, app_name=target_app_name)
    spec_dict = await spec.to_dict()
    relations = await FieldGroupFieldSpec.filter(field_spec_id=spec.id).all()
    group_ids = [r.field_group_id for r in relations]
    spec_dict['field_group_ids'] = group_ids
    groups = await field_group_config_controller.model.filter(id__in=group_ids).all()
    spec_dict['field_groups'] = [{"id": g.id, "group_name": g.group_name, "group_code": g.group_code} for g in groups]
    return Success(data=spec_dict)


@router.post("/field_spec/update", summary="更新字段明细")
async def update_field_spec(spec_in: FieldSpecUpdate, token: str = Header(...)):
    await AuthControl.is_authed(token)
    spec = await field_spec_controller.get(id=spec_in.id)

    if not TenantContext.is_superuser() and spec.tenant_id != TenantContext.get_tenant_id():
        return Fail(code=403, msg="无权操作其他租户的字段")

    if spec_in.field_group_ids:
        for group_id in spec_in.field_group_ids:
            group = await field_group_config_controller.get(id=group_id)
            if not group:
                return Fail(code=400, msg=f"字段组(ID:{group_id})不存在")
            if not TenantContext.is_superuser() and group.tenant_id != TenantContext.get_tenant_id():
                return Fail(code=403, msg=f"无权操作字段组(ID:{group_id})")

    updated = await field_spec_controller.update_field_spec(id=spec_in.id, obj_in=spec_in, tenant_id=spec.tenant_id, app_name=spec.app_name)
    spec_dict = await updated.to_dict()
    relations = await FieldGroupFieldSpec.filter(field_spec_id=updated.id).all()
    group_ids = [r.field_group_id for r in relations]
    spec_dict['field_group_ids'] = group_ids
    groups = await field_group_config_controller.model.filter(id__in=group_ids).all()
    spec_dict['field_groups'] = [{"id": g.id, "group_name": g.group_name, "group_code": g.group_code} for g in groups]
    return Success(data=spec_dict)


@router.delete("/field_spec/delete", summary="删除字段明细")
async def delete_field_spec(id: int = Query(...), token: str = Header(...)):
    current_user = await AuthControl.is_authed(token)
    spec = await field_spec_controller.get(id=id)

    # 使用公共方法验证删除权限
    success, msg = TenantControl.validate_delete_permission(
        current_user, spec.tenant_id
    )
    if not success:
        return Fail(code=403, msg=msg)

    await field_spec_controller.remove(id=id)
    return Success(msg="删除成功")


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


@router.post("/field_spec/export", summary="导出字段明细")
async def export_field_specs(export_in: Dict[str, Any], token: str = Header(...)):
    await AuthControl.is_authed(token)
    ids = export_in.get('ids', [])

    query = Q(id__in=ids)
    if not TenantContext.is_superuser():
        query &= Q(tenant_id=TenantContext.get_tenant_id())

    specs = await field_spec_controller.model.filter(query).all()
    if not specs:
        return Fail(code=404, msg="未找到要导出的字段")

    base_output = io.StringIO()
    base_writer = csv.writer(base_output)
    base_writer.writerow(['ID', '字段名', '字段标签', '字段类型', '填写指引', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])

    options_output = io.StringIO()
    options_writer = csv.writer(options_output)
    options_writer.writerow(['字段ID', '字段名', '选项值', '选项标签', '填写说明', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])

    for spec in specs:
        relations = await FieldGroupFieldSpec.filter(field_spec_id=spec.id).all()
        groups_data = []
        tenant_domain = ""

        if relations:
            group_ids = [r.field_group_id for r in relations]
            groups = await FieldGroupConfig.filter(id__in=group_ids).all()
            page_ids = [g.page_id for g in groups if g.page_id > 0]
            pages_map = {}
            if page_ids:
                pages = await FillPage.filter(id__in=page_ids).all()
                pages_map = {p.id: p.page_name for p in pages}

            for g in groups:
                groups_data.append({'group_name': g.group_name, 'page_name': pages_map.get(g.page_id, '')})

        if spec.tenant_id > 0:
            tenant = await Tenant.filter(id=spec.tenant_id).first()
            if tenant:
                tenant_domain = tenant.domain

        status_str = '启用' if spec.is_active else '已删除'
        corrections_text = ''
        if spec.corrections:
            corrections_text = '\n'.join(['*' + c.get('text', '') for c in spec.corrections if c.get('text')])

        if not groups_data:
            base_writer.writerow([spec.id, spec.field_name, spec.field_label or '', spec.field_type.value if spec.field_type else '', spec.fill_instruction or '', corrections_text, status_str, tenant_domain, '', ''])
        else:
            for group_info in groups_data:
                base_writer.writerow([spec.id, spec.field_name, spec.field_label or '', spec.field_type.value if spec.field_type else '', spec.fill_instruction or '', corrections_text, status_str, tenant_domain, group_info['group_name'], group_info['page_name']])

        if spec.field_type in ['select_single', 'select_multi'] and spec.options:
            items = spec.options.get('items', [])
            for item in items:
                option_corrections = item.get('corrections', '')
                if isinstance(option_corrections, list):
                    option_corrections = '\n'.join(['*' + c.get('text', '') for c in option_corrections if c.get('text')])
                option_status = '已删除' if item.get('is_deleted') else '启用'

                if not groups_data:
                    options_writer.writerow([spec.id, spec.field_name, item.get('value', ''), item.get('label', ''), item.get('fill_instruction', ''), option_corrections, option_status, tenant_domain, '', ''])
                else:
                    for group_info in groups_data:
                        options_writer.writerow([spec.id, spec.field_name, item.get('value', ''), item.get('label', ''), item.get('fill_instruction', ''), option_corrections, option_status, tenant_domain, group_info['group_name'], group_info['page_name']])

    return Success(data={"base_csv": base_output.getvalue(), "options_csv": options_output.getvalue()})


@router.post("/field_spec/import", summary="导入字段明细")
async def import_field_specs(
    base_file: UploadFile = File(None),
    options_file: UploadFile = File(None),
    token: str = Header(...),
):
    from app.services.autofill.field_spec_service import find_field_by_unique_key
    await AuthControl.is_authed(token)

    tenant_id = TenantContext.get_tenant_id()
    app_name = "autofill"

    if not base_file and not options_file:
        return Fail(code=400, msg="请至少上传一个CSV文件")

    success_count = 0
    delete_count = 0
    error_messages = []

    if base_file and base_file.filename.endswith('.csv'):
        try:
            content = await base_file.read()
            csv_reader = csv.DictReader(io.StringIO(content.decode('utf-8')))
            for row in csv_reader:
                try:
                    field_name = (row.get('字段名') or '').strip()
                    field_label = (row.get('字段标签') or '').strip()
                    field_type = (row.get('字段类型') or '').strip()
                    fill_instruction = (row.get('填写指引') or '').strip()
                    corrections_text = (row.get('corrections') or '').strip()
                    status = (row.get('状态') or '').strip()
                    tenant_domain = (row.get('租户域名') or '').strip()
                    group_name = (row.get('字段组名称') or '').strip()
                    page_name = (row.get('页面名称') or '').strip()

                    if not field_name:
                        continue

                    field_spec, group = await find_field_by_unique_key(
                        tenant_domain=tenant_domain, page_name=page_name, group_name=group_name,
                        field_name=field_name, tenant_id=tenant_id if not TenantContext.is_superuser() else None
                    )

                    corrections = []
                    if corrections_text:
                        for line in corrections_text.split('\n'):
                            line = line.strip()
                            if line.startswith('*'):
                                text = line[1:].strip()
                                if text:
                                    corrections.append({"text": text})

                    if field_spec:
                        if status == '已删除':
                            field_spec.is_active = False
                            await field_spec.save()
                            delete_count += 1
                            continue
                        field_spec.field_label = field_label or field_spec.field_label
                        field_spec.fill_instruction = fill_instruction
                        field_spec.corrections = corrections
                        field_spec.is_active = True
                        await field_spec.save()
                        success_count += 1
                    else:
                        if status == '已删除':
                            continue
                        target_tenant_id = tenant_id
                        if tenant_domain:
                            tenant = await Tenant.filter(domain=tenant_domain).first()
                            if tenant:
                                target_tenant_id = tenant.id

                        target_group_id = group.id if group else None
                        if not target_group_id and group_name:
                            search_tenant_id = target_tenant_id if target_tenant_id > 0 else tenant_id
                            group_query = Q(group_name=group_name)
                            if search_tenant_id > 0:
                                group_query &= Q(tenant_id=search_tenant_id)
                            if page_name:
                                group_query &= Q(page_name=page_name)
                            group = await FieldGroupConfig.filter(group_query).first()
                            if group:
                                target_group_id = group.id

                        await upsert_field_spec(
                            tenant_id=target_tenant_id if target_tenant_id > 0 else tenant_id,
                            app_name=app_name, field_name=field_name, field_label=field_label or field_name,
                            field_type=field_type or 'text', field_group_ids=[target_group_id] if target_group_id else [],
                            fill_instruction=fill_instruction,
                            options={'items': []} if field_type in ['select_single', 'select_multi'] else None,
                            sync_mode='merge'
                        )
                        success_count += 1
                except Exception as e:
                    error_messages.append(f"处理基础字段行失败: {str(e)}")
        except Exception as e:
            error_messages.append(f"读取基础字段文件失败: {str(e)}")

    if options_file and options_file.filename.endswith('.csv'):
        try:
            content = await options_file.read()
            csv_reader = csv.DictReader(io.StringIO(content.decode('utf-8')))
            for row in csv_reader:
                try:
                    field_name = (row.get('字段名') or '').strip()
                    option_value = (row.get('选项值') or '').strip()
                    option_label = (row.get('选项标签') or '').strip()
                    fill_instruction = (row.get('填写说明') or '').strip()
                    corrections_text = (row.get('corrections') or '').strip()
                    status = (row.get('状态') or '').strip()
                    tenant_domain = (row.get('租户域名') or '').strip()
                    group_name = (row.get('字段组名称') or '').strip()
                    page_name = (row.get('页面名称') or '').strip()

                    if not field_name or not option_value:
                        continue

                    field_spec, group = await find_field_by_unique_key(
                        tenant_domain=tenant_domain, page_name=page_name, group_name=group_name,
                        field_name=field_name, tenant_id=tenant_id if not TenantContext.is_superuser() else None
                    )

                    if not field_spec:
                        if status == '已删除':
                            continue
                        target_tenant_id = tenant_id
                        if tenant_domain:
                            tenant = await Tenant.filter(domain=tenant_domain).first()
                            if tenant:
                                target_tenant_id = tenant.id
                        target_group_id = group.id if group else None
                        if not target_group_id and group_name:
                            search_tenant_id = target_tenant_id if target_tenant_id > 0 else tenant_id
                            group_query = Q(group_name=group_name)
                            if search_tenant_id > 0:
                                group_query &= Q(tenant_id=search_tenant_id)
                            if page_name:
                                group_query &= Q(page_name=page_name)
                            group = await FieldGroupConfig.filter(group_query).first()
                            if group:
                                target_group_id = group.id
                        result = await upsert_field_spec(
                            tenant_id=target_tenant_id if target_tenant_id > 0 else tenant_id,
                            app_name=app_name, field_name=field_name, field_label=field_name,
                            field_type='select_single', field_group_ids=[target_group_id] if target_group_id else [],
                            fill_instruction='', options={'items': []}, sync_mode='merge'
                        )
                        field_spec = result.get('field_spec')

                    if status == '已删除':
                        options = field_spec.options or {}
                        items = options.get('items', [])
                        items = [item for item in items if str(item.get('value', '')) != option_value]
                        options['items'] = items
                        field_spec.options = options
                        await field_spec.save()
                        delete_count += 1
                        continue

                    corrections = []
                    if corrections_text:
                        for line in corrections_text.split('\n'):
                            line = line.strip()
                            if line.startswith('*'):
                                text = line[1:].strip()
                                if text:
                                    corrections.append({"text": text})

                    option_items = [{'value': option_value, 'label': option_label, 'fill_instruction': fill_instruction, 'corrections': corrections, 'is_deleted': False}]
                    existing_options = field_spec.options or {}
                    existing_items = existing_options.get('items', [])
                    merged_items_map = {}
                    for item in existing_items:
                        if isinstance(item, dict) and 'label' in item:
                            merged_items_map[item['label']] = item
                    for new_item in option_items:
                        label = new_item['label']
                        if label in merged_items_map:
                            existing = merged_items_map[label]
                            existing['value'] = new_item['value']
                            existing['fill_instruction'] = new_item['fill_instruction']
                            existing['corrections'] = new_item['corrections']
                            existing['is_deleted'] = False
                        else:
                            merged_items_map[label] = new_item
                    existing_options['items'] = list(merged_items_map.values())
                    field_spec.options = existing_options
                    await field_spec.save()
                    success_count += 1
                except Exception as e:
                    error_messages.append(f"处理选项行失败: {str(e)}")
        except Exception as e:
            error_messages.append(f"读取选项文件失败: {str(e)}")

    result = {"success_count": success_count, "delete_count": delete_count, "errors": error_messages[:10]}
    if error_messages:
        result["error_count"] = len(error_messages)
    return Success(data=result)


@router.post("/field_spec/sync_options", summary="同步字段选项")
async def sync_field_spec_options(sync_in: FieldSpecSyncOptionsRequest, token: str = Header(...)):
    await AuthControl.is_authed(token)
    tenant_id = TenantContext.get_tenant_id()

    if not sync_in.field_name:
        return Fail(code=400, msg="字段名称不能为空")
    if not sync_in.field_label:
        return Fail(code=400, msg="字段标签不能为空")
    if not sync_in.field_group_ids:
        return Fail(code=400, msg="请至少选择一个关联字段组")
    if not sync_in.options.api_schema:
        return Fail(code=400, msg="请先配置OpenAPI Schema")

    try:
        spec = parse_openapi_schema(sync_in.options.api_schema)
        base_url, path, method, operation = get_endpoint_config(spec)
        full_url = f"{base_url.rstrip('/')}{path}"

        x_api_params = operation.get('x-api-params', {})
        headers = x_api_params.get('headers', {}).copy()
        for h in (sync_in.options.api_headers or []):
            if h.key and h.value:
                headers[h.key] = h.value
        params = {k: v for k, v in x_api_params.items() if k != 'headers'}

        json_body = None
        request_body = operation.get('requestBody', {})
        if request_body and method == 'post':
            content = request_body.get('content', {})
            if 'application/json' in content:
                schema = content['application/json'].get('schema', {})
                json_body = {}
                for prop_name, prop_schema in schema.get('properties', {}).items():
                    if 'default' in prop_schema:
                        json_body[prop_name] = prop_schema['default']
                    elif 'example' in prop_schema:
                        json_body[prop_name] = prop_schema['example']
                json_body.update(params)

        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == 'get':
                response = await client.get(full_url, headers=headers, params=params)
            else:
                headers.setdefault('Content-Type', 'application/json')
                response = await client.post(full_url, headers=headers, json=json_body or params)
            response.raise_for_status()
            response_data = response.json()

        x_mapping = operation.get('x-field-mapping', {})
        label_path = x_mapping.get('label_path', '$.data[*].label')
        value_path = x_mapping.get('value_path', '$.data[*].value')
        enable_flatten = x_mapping.get('enable_flatten', False)
        flatten_config = x_mapping.get('flatten_config', None)

        new_items = []
        if enable_flatten and flatten_config:
            new_items = FieldFlattener.flatten_field_options(response_data, flatten_config)
        else:
            try:
                label_expr = jsonpath_parse(label_path)
                label_results = [match.value for match in label_expr.find(response_data)]
                value_expr = jsonpath_parse(value_path)
                value_results = [match.value for match in value_expr.find(response_data)]
            except Exception as e:
                return Fail(code=400, msg=f"字段映射路径解析错误: {str(e)}")

            if not label_results:
                return Fail(code=400, msg="API返回数据格式不正确，未找到选项列表")

            for i, label in enumerate(label_results):
                value = value_results[i] if i < len(value_results) else label
                label = str(label) if label is not None else ''
                value = str(value) if value is not None else ''
                if not label:
                    continue
                new_items.append({'value': value, 'label': label, 'fill_instruction': '', 'corrections': [], 'is_deleted': False})

        tenant_filter = {"tenant_id": tenant_id} if tenant_id > 0 else {}
        field_group = await FieldGroupConfig.filter(id=sync_in.field_group_ids[0], **tenant_filter).first()
        if not field_group:
            return Fail(code=400, msg="字段组不存在或无权限访问")

        app_name = field_group.app_name
        options_data = {
            'items': new_items,
            'min_selections': sync_in.options.min_selections or 1,
            'max_selections': sync_in.options.max_selections or 0,
            'api_schema': sync_in.options.api_schema,
            'api_headers': [{'key': h.key, 'value': h.value} for h in (sync_in.options.api_headers or [])]
        }

        result = await upsert_field_spec(
            tenant_id=tenant_id, app_name=app_name, field_name=sync_in.field_name, field_label=sync_in.field_label,
            field_type=sync_in.field_type, field_group_ids=sync_in.field_group_ids,
            fill_instruction=sync_in.fill_instruction, options=options_data, sync_mode='replace', delete_not_exist=True
        )

        field_spec = result["field_spec"]
        updated_count = result["updated_count"]
        final_items = result["items"]

        return Success(data={"items": final_items, "updated_count": updated_count, "field_id": field_spec.id, "message": f"同步成功，共更新 {updated_count} 个选项"})

    except ValueError as e:
        return Fail(code=400, msg=f"Schema解析错误: {str(e)}")
    except yaml.YAMLError as e:
        return Fail(code=400, msg=f"Schema YAML格式错误: {str(e)}")
    except httpx.HTTPError as e:
        return Fail(code=400, msg=f"请求API失败: {str(e)}")
    except Exception as e:
        return Fail(code=500, msg=f"同步失败: {str(e)}")


@router.post("/field_spec/parse_curl", summary="解析 curl 命令生成 OpenAPI Schema")
async def parse_curl_command_endpoint(request: CurlParseRequest, token: str = Header(...)):
    await AuthControl.is_authed(token)

    if not request.curl_command or not request.curl_command.strip():
        return Fail(code=400, msg="curl 命令不能为空")

    try:
        parsed = parse_curl_command(request.curl_command)

        async with httpx.AsyncClient(timeout=30.0) as client:
            method = parsed['method'].lower()
            url = parsed['url']
            headers = parsed['headers']
            body = parsed['body']

            if method == 'get':
                response = await client.get(url, headers=headers)
            elif method == 'post':
                response = await client.post(url, headers=headers, json=body) if body and isinstance(body, dict) else await client.post(url, headers=headers)
            elif method == 'put':
                response = await client.put(url, headers=headers, json=body) if body and isinstance(body, dict) else await client.put(url, headers=headers)
            elif method == 'patch':
                response = await client.patch(url, headers=headers, json=body) if body and isinstance(body, dict) else await client.patch(url, headers=headers)
            elif method == 'delete':
                response = await client.delete(url, headers=headers)
            else:
                return Fail(code=400, msg=f"不支持的 HTTP 方法: {method}")

            response.raise_for_status()
            response_data = response.json()

        flatten_config = None
        if request.enable_flatten:
            flatten_config = {
                'label_path_level1': request.flatten_label_path_level1 or request.label_path,
                'label_path_level2': request.flatten_label_path_level2,
                'label_path_level3': request.flatten_label_path_level3,
                'label_separator': request.flatten_label_separator,
                'value_path_level1': request.flatten_value_path_level1 or request.value_path,
                'value_path_level2': request.flatten_value_path_level2,
                'value_path_level3': request.flatten_value_path_level3,
                'value_separator': request.flatten_value_separator
            }

        openapi_dict = generate_openapi_schema_from_curl(
            request.curl_command, response_data, label_path=request.label_path, value_path=request.value_path,
            enable_flatten=request.enable_flatten, flatten_config=flatten_config
        )
        openapi_yaml = yaml.dump(openapi_dict, allow_unicode=True, sort_keys=False)

        return Success(data={"openapi_schema": openapi_yaml, "response_preview": response_data, "message": "curl 解析成功，已生成 OpenAPI Schema"})

    except ValueError as e:
        return Fail(code=400, msg=f"curl 命令解析错误: {str(e)}")
    except httpx.HTTPError as e:
        return Fail(code=400, msg=f"执行 curl 请求失败: {str(e)}")
    except json.JSONDecodeError as e:
        return Fail(code=400, msg=f"响应数据不是有效的 JSON: {str(e)}")
    except Exception as e:
        return Fail(code=500, msg=f"解析失败: {str(e)}")
