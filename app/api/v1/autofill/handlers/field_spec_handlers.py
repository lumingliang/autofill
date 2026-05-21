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
from fastapi import APIRouter, BackgroundTasks, File, Header, Query, UploadFile
from jsonpath_ng import parse as jsonpath_parse
from pydantic import BaseModel
from tortoise.expressions import Q

from app.controllers.autofill import field_group_config_controller, field_spec_controller
from app.core.dependency import AuthControl, TenantControl
from app.core.tenant import TenantContext
from app.models.admin import Tenant
from app.models.autofill import FieldGroupFieldSpec, FieldGroupConfig, FieldSpec, FieldType
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.fill_page import (
    FieldSpecCreate, FieldSpecUpdate, FieldSpecSyncOptionsRequest,
    CurlParseRequest, ApplyFieldMappingRequest, SyncTemplateFieldRequest,
    TemplateCurlParseRequest, TemplateCurlApplyRequest, TemplateFieldMapping
)
from app.services.autofill.field_spec_service import upsert_field_spec
from app.services.autofill.field_flatten_service import FieldFlattener
from app.utils.curl_parser import parse_curl_command, generate_openapi_schema_from_curl, generate_template_schema_from_curl

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
            # 如果字段组下没有字段，返回空结果
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

    # 使用公共方法验证租户ID
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

    # 使用公共方法验证删除权限
    success, msg = TenantControl.validate_delete_permission(
        current_user, spec.tenant_id
    )
    if not success:
        return Fail(code=403, msg=msg)

    await field_spec_controller.remove(id=id)
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

            # 使用公共方法验证删除权限
            success, msg = TenantControl.validate_delete_permission(
                current_user, spec.tenant_id
            )
            if not success:
                failed_count += 1
                failed_ids.append(field_id)
                continue

            await field_spec_controller.remove(id=field_id)
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

    # 检查字段组是否存在
    group = await field_group_config_controller.get(id=field_group_id)
    if not group:
        return Fail(code=400, msg="字段组不存在")

    # 权限检查
    if not TenantContext.is_superuser() and group.tenant_id != TenantContext.get_tenant_id():
        return Fail(code=403, msg="无权操作其他租户的字段组")

    success_count = 0
    failed_count = 0

    for field_spec_id in field_spec_ids:
        # 检查字段是否存在
        field = await field_spec_controller.get(id=field_spec_id)
        if not field:
            failed_count += 1
            continue

        # 检查字段是否属于同一租户
        if field.tenant_id != group.tenant_id:
            failed_count += 1
            continue

        # 检查关联是否已存在
        existing = await FieldGroupFieldSpec.filter(
            field_group_id=field_group_id,
            field_spec_id=field_spec_id
        ).first()
        if existing:
            success_count += 1  # 已存在也算成功
            continue

        # 创建关联，使用字段组的app_name
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

    # 检查字段组是否存在
    group = await FieldGroupConfig.filter(id=field_group_id).first()
    if not group:
        return Fail(code=404, msg="字段组不存在")

    removed_count = 0
    failed_count = 0

    for field_spec_id in field_spec_ids:
        # 检查关联是否存在
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


@router.post("/field_spec/sync_options", summary="同步字段选项")
async def sync_field_spec_options(sync_in: FieldSpecSyncOptionsRequest, token: str = Header(...)):
    await AuthControl.is_authed(token)

    if not sync_in.field_name:
        return Fail(code=400, msg="字段名称不能为空")
    if not sync_in.field_label:
        return Fail(code=400, msg="字段标签不能为空")
    if not sync_in.options.api_schema:
        return Fail(code=400, msg="请先配置OpenAPI Schema")

    # TODO: 需要传入tenant_id和app_name参数，暂时使用默认值
    # 后续需要从前端传入这些参数
    tenant_id = TenantContext.get_tenant_id() if not TenantContext.is_superuser() else 0
    app_name = "autofill"

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

        options_data = {
            'items': new_items,
            'min_selections': sync_in.options.min_selections or 1,
            'max_selections': sync_in.options.max_selections or 0,
            'api_schema': sync_in.options.api_schema,
            'api_headers': [{'key': h.key, 'value': h.value} for h in (sync_in.options.api_headers or [])]
        }

        result = await upsert_field_spec(
            tenant_id=tenant_id, app_name=app_name, field_name=sync_in.field_name, field_label=sync_in.field_label,
            field_type=sync_in.field_type,
            fill_instruction=sync_in.fill_instruction, options=options_data, delete_not_exist=True
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

        # 如果没有提供 label_path 和 value_path，则生成基础 schema（用于第一步）
        label_path = request.label_path or "$.data[*].label"
        value_path = request.value_path or "$.data[*].value"

        flatten_config = None
        if request.enable_flatten:
            flatten_config = {
                'label_path_level1': request.flatten_label_path_level1 or label_path,
                'label_path_level2': request.flatten_label_path_level2,
                'label_path_level3': request.flatten_label_path_level3,
                'label_separator': request.flatten_label_separator,
                'value_path_level1': request.flatten_value_path_level1 or value_path,
                'value_path_level2': request.flatten_value_path_level2,
                'value_path_level3': request.flatten_value_path_level3,
                'value_separator': request.flatten_value_separator
            }

        openapi_dict = generate_openapi_schema_from_curl(
            request.curl_command, response_data, label_path=label_path, value_path=value_path,
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


@router.post("/field_spec/apply_mapping", summary="应用字段映射到 OpenAPI Schema")
async def apply_field_mapping_endpoint(request: ApplyFieldMappingRequest, token: str = Header(...)):
    """
    将字段映射配置应用到已解析的 OpenAPI Schema
    """
    await AuthControl.is_authed(token)

    if not request.openapi_schema or not request.openapi_schema.strip():
        return Fail(code=400, msg="OpenAPI Schema 不能为空")

    try:
        # 解析现有的 schema
        schema = yaml.safe_load(request.openapi_schema)

        # 更新 x-field-mapping 配置
        if 'paths' in schema:
            for path, methods in schema['paths'].items():
                for method, operation in methods.items():
                    if isinstance(operation, dict):
                        if 'x-field-mapping' not in operation:
                            operation['x-field-mapping'] = {}

                        operation['x-field-mapping']['label_path'] = request.label_path
                        operation['x-field-mapping']['value_path'] = request.value_path

                        # 添加展平配置
                        if request.enable_flatten and request.flatten_config:
                            operation['x-field-mapping']['enable_flatten'] = True
                            operation['x-field-mapping']['flatten_config'] = {
                                'label_path_level1': request.flatten_config.label_path_level1 or request.label_path,
                                'label_path_level2': request.flatten_config.label_path_level2,
                                'label_path_level3': request.flatten_config.label_path_level3,
                                'label_separator': request.flatten_config.label_separator,
                                'value_path_level1': request.flatten_config.value_path_level1 or request.value_path,
                                'value_path_level2': request.flatten_config.value_path_level2,
                                'value_path_level3': request.flatten_config.value_path_level3,
                                'value_separator': request.flatten_config.value_separator,
                            }

        # 重新生成 YAML
        openapi_yaml = yaml.dump(schema, allow_unicode=True, sort_keys=False)

        return Success(data={"openapi_schema": openapi_yaml, "message": "字段映射配置成功"})

    except yaml.YAMLError as e:
        return Fail(code=400, msg=f"YAML 解析错误: {str(e)}")
    except Exception as e:
        return Fail(code=500, msg=f"应用字段映射失败: {str(e)}")


@router.post("/field_spec/sync", summary="同步模板类型字段")
async def sync_template_field(
    request: SyncTemplateFieldRequest,
    bg_tasks: BackgroundTasks,
    token: str = Header(...)
):
    """
    触发模板类型字段的同步

    流程：
    1. 验证字段存在且类型为template
    2. 创建同步记录，状态pending
    3. 添加后台任务
    4. 返回同步记录ID
    """
    current_user = await AuthControl.is_authed(token)

    # 获取字段信息
    field_spec = await FieldSpec.get(id=request.field_spec_id)
    if not field_spec:
        return Fail(code=404, msg="字段不存在")

    # 权限检查
    if not TenantContext.is_superuser() and field_spec.tenant_id != TenantContext.get_tenant_id():
        return Fail(code=403, msg="无权操作其他租户的字段")

    # 验证字段类型
    if field_spec.field_type != FieldType.TEMPLATE:
        return Fail(code=400, msg="仅支持模板类型字段的同步")

    # 检查是否有api_schema配置（支持新的YAML格式）
    api_schema = field_spec.options.get("api_schema")
    if not api_schema:
        return Fail(code=400, msg="字段缺少api_schema配置")

    # 调用服务层进行同步
    from app.services.autofill.template_field_service import template_field_service

    try:
        result = await template_field_service.sync_template_field(
            field_spec_id=request.field_spec_id,
            bg_tasks=bg_tasks
        )
        return Success(data=result)
    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except Exception as e:
        return Fail(code=500, msg=f"同步失败: {str(e)}")


@router.get("/field_spec/sync_status", summary="查询字段同步状态")
async def get_sync_status(
    sync_record_id: int = Query(0, description="同步记录ID"),
    field_spec_id: int = Query(0, description="字段ID（优先使用）"),
    token: str = Header(...)
):
    """
    查询模板类型字段的同步状态

    支持两种查询方式：
    1. 通过 field_spec_id 查询该字段最新的同步记录
    2. 通过 sync_record_id 查询指定的同步记录
    """
    current_user = await AuthControl.is_authed(token)

    # 获取同步记录
    from app.services.autofill.template_field_service import template_field_service
    from app.models.autofill import FieldSpecSyncRecord

    try:
        # 优先使用 field_spec_id 查询最新的同步记录
        if field_spec_id > 0:
            record = await FieldSpecSyncRecord.filter(
                field_spec_id=field_spec_id
            ).order_by("-created_at").first()
            if not record:
                return Success(data={
                    "status": "none",
                    "message": "该字段暂无同步记录"
                })
            sync_record_id = record.id
        elif sync_record_id <= 0:
            return Fail(code=400, msg="请提供 sync_record_id 或 field_spec_id")

        result = await template_field_service.get_sync_status(sync_record_id)

        # 权限检查
        if not TenantContext.is_superuser():
            # 获取字段信息以检查租户
            field_spec = await FieldSpec.get(id=result["field_spec_id"])
            if field_spec.tenant_id != TenantContext.get_tenant_id():
                return Fail(code=403, msg="无权查看其他租户的同步记录")

        return Success(data=result)
    except Exception as e:
        return Fail(code=500, msg=f"查询失败: {str(e)}")


@router.post("/field_spec/template/parse_curl", summary="解析模板类型 CURL 命令生成 Schema")
async def parse_template_curl_endpoint(request: TemplateCurlParseRequest, token: str = Header(...)):
    """
    解析模板类型的 curl 命令生成 OpenAPI Schema

    流程：
    1. 解析 curl 命令
    2. 执行请求获取响应数据
    3. 生成包含 x-template-mapping 的 OpenAPI Schema
    """
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

        # 生成模板类型的 OpenAPI Schema
        openapi_dict = generate_template_schema_from_curl(
            request.curl_command,
            response_data,
            template_name_path=request.template_name_path,
            template_content_path=request.template_content_path
        )
        openapi_yaml = yaml.dump(openapi_dict, allow_unicode=True, sort_keys=False)

        return Success(data={"openapi_schema": openapi_yaml, "response_preview": response_data, "message": "curl 解析成功，已生成模板类型 Schema"})

    except ValueError as e:
        return Fail(code=400, msg=f"curl 命令解析错误: {str(e)}")
    except httpx.HTTPError as e:
        return Fail(code=400, msg=f"执行 curl 请求失败: {str(e)}")
    except json.JSONDecodeError as e:
        return Fail(code=400, msg=f"响应数据不是有效的 JSON: {str(e)}")
    except Exception as e:
        return Fail(code=500, msg=f"解析失败: {str(e)}")


@router.post("/field_spec/template/apply_mapping", summary="应用模板类型字段映射到 Schema")
async def apply_template_field_mapping_endpoint(request: TemplateCurlApplyRequest, token: str = Header(...)):
    """
    将模板类型的字段映射配置应用到已解析的 OpenAPI Schema
    """
    await AuthControl.is_authed(token)

    if not request.openapi_schema or not request.openapi_schema.strip():
        return Fail(code=400, msg="OpenAPI Schema 不能为空")

    try:
        # 解析现有的 schema
        schema = yaml.safe_load(request.openapi_schema)

        # 更新 x-template-mapping 配置
        if 'paths' in schema:
            for path, methods in schema['paths'].items():
                for method, operation in methods.items():
                    if isinstance(operation, dict):
                        if 'x-template-mapping' not in operation:
                            operation['x-template-mapping'] = {}

                        operation['x-template-mapping']['template_name_path'] = request.field_mapping.template_name_path
                        operation['x-template-mapping']['template_content_path'] = request.field_mapping.template_content_path
                        operation['x-template-mapping']['group_name_pattern'] = request.field_mapping.group_name_pattern

                        if request.field_mapping.parse_prompt:
                            operation['x-template-mapping']['parse_prompt'] = request.field_mapping.parse_prompt

                        # 添加模板选择器配置
                        selector = request.field_mapping.template_selector
                        if selector.enabled:
                            operation['x-template-mapping']['template_selector'] = {
                                'enabled': selector.enabled,
                                'field_name': selector.field_name,
                                'field_label': selector.field_label,
                                'label_path': selector.label_path,
                                'value_path': selector.value_path
                            }

        # 重新生成 YAML
        openapi_yaml = yaml.dump(schema, allow_unicode=True, sort_keys=False)

        return Success(data={"openapi_schema": openapi_yaml, "message": "模板字段映射配置成功"})

    except yaml.YAMLError as e:
        return Fail(code=400, msg=f"YAML 解析错误: {str(e)}")
    except Exception as e:
        return Fail(code=500, msg=f"应用字段映射失败: {str(e)}")
