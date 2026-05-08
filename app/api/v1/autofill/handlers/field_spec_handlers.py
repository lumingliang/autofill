"""
字段明细管理接口
"""
import csv
import io
from datetime import datetime
from typing import List

import httpx
import yaml
from fastapi import APIRouter, File, Header, Query, UploadFile
from jsonpath_ng import parse as jsonpath_parse
from pydantic import BaseModel
from tortoise.expressions import Q

from app.controllers.autofill import (
    field_group_config_controller,
    field_spec_controller,
)
from app.controllers.tenant import tenant_controller
from app.core.dependency import AuthControl, is_superuser, build_tenant_query
from app.models.admin import Tenant
from app.models.autofill import FieldGroupFieldSpec, FieldGroupConfig, FillPage
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.fill_page import FieldSpecCreate, FieldSpecUpdate, FieldSpecSyncOptionsRequest
from app.services.autofill.field_spec_service import upsert_field_spec

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
    1. 基础字段信息（ID, 字段名, 字段标签, 字段类型, 填写指引, corrections, 状态, 租户域名, 字段组名称, 页面名称）
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

    # 准备基础字段CSV - 增加租户域名、字段组名称、页面名称、状态字段
    base_output = io.StringIO()
    base_writer = csv.writer(base_output)
    base_writer.writerow(['ID', '字段名', '字段标签', '字段类型', '填写指引', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])

    # 准备选项详情CSV - 增加租户域名、字段组名称、页面名称、状态字段
    options_output = io.StringIO()
    options_writer = csv.writer(options_output)
    options_writer.writerow(['字段ID', '字段名', '选项值', '选项标签', '填写说明', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])

    for spec in specs:
        # 获取字段关联的字段组和页面信息
        relations = await FieldGroupFieldSpec.filter(field_spec_id=spec.id).all()
        groups_data = []
        tenant_domain = ""

        if relations:
            group_ids = [r.field_group_id for r in relations]
            groups = await FieldGroupConfig.filter(id__in=group_ids).all()
            
            # 获取页面名称
            page_ids = [g.page_id for g in groups if g.page_id > 0]
            pages_map = {}
            if page_ids:
                pages = await FillPage.filter(id__in=page_ids).all()
                pages_map = {p.id: p.page_name for p in pages}
            
            for g in groups:
                page_name = pages_map.get(g.page_id, '')
                groups_data.append({
                    'group_name': g.group_name,
                    'page_name': page_name
                })

        # 获取租户域名
        if spec.tenant_id > 0:
            tenant = await Tenant.filter(id=spec.tenant_id).first()
            if tenant:
                tenant_domain = tenant.domain

        status_str = '启用' if spec.is_active else '已删除'

        # 写入基础字段信息 - 为每个字段组单独导出一行
        corrections_text = ''
        if spec.corrections:
            # 每行都以 * 开头
            corrections_text = '\n'.join(['*' + c.get('text', '') for c in spec.corrections if c.get('text')])

        # 如果没有关联字段组，导出一行空字段组的数据
        if not groups_data:
            base_writer.writerow([
                spec.id,
                spec.field_name,
                spec.field_label or '',
                spec.field_type.value if spec.field_type else '',
                spec.fill_instruction or '',
                corrections_text,
                status_str,
                tenant_domain,
                '',  # 字段组名称
                '',  # 页面名称
            ])
        else:
            # 为每个字段组导出一行
            for group_info in groups_data:
                base_writer.writerow([
                    spec.id,
                    spec.field_name,
                    spec.field_label or '',
                    spec.field_type.value if spec.field_type else '',
                    spec.fill_instruction or '',
                    corrections_text,
                    status_str,
                    tenant_domain,
                    group_info['group_name'],
                    group_info['page_name'],
                ])

        # 写入选项详情（仅下拉单选/多选类型）
        if spec.field_type in ['select_single', 'select_multi'] and spec.options:
            items = spec.options.get('items', [])
            for item in items:
                # 处理选项的corrections
                option_corrections = item.get('corrections', '')
                if isinstance(option_corrections, list):
                    # 每行都以 * 开头
                    option_corrections = '\n'.join(['*' + c.get('text', '') for c in option_corrections if c.get('text')])

                # 选项状态
                option_status = '已删除' if item.get('is_deleted') else '启用'

                # 为每个字段组导出一行选项
                if not groups_data:
                    options_writer.writerow([
                        spec.id,
                        spec.field_name,
                        item.get('value', ''),
                        item.get('label', ''),
                        item.get('fill_instruction', ''),
                        option_corrections,
                        option_status,
                        tenant_domain,
                        '',  # 字段组名称
                        ''   # 页面名称
                    ])
                else:
                    for group_info in groups_data:
                        options_writer.writerow([
                            spec.id,
                            spec.field_name,
                            item.get('value', ''),
                            item.get('label', ''),
                            item.get('fill_instruction', ''),
                            option_corrections,
                            option_status,
                            tenant_domain,
                            group_info['group_name'],
                            group_info['page_name']
                        ])

    return Success(data={
        "base_csv": base_output.getvalue(),
        "options_csv": options_output.getvalue()
    })


@router.post("/field_spec/import", summary="导入字段明细")
async def import_field_specs(
    base_file: UploadFile = File(None, description="基础字段信息CSV文件"),
    options_file: UploadFile = File(None, description="选项详情CSV文件"),
    token: str = Header(..., description="token验证"),
):
    """
    从CSV文件导入字段明细
    支持上传两个CSV文件：
    1. 基础字段信息（ID, 字段名, 字段标签, 字段类型, 填写指引, corrections, 状态, 租户域名, 字段组名称, 页面名称, 选项来源）
    2. 选项详情（字段ID, 字段名, 选项值, 选项标签, 填写说明, corrections, 状态, 租户域名, 字段组名称, 页面名称）

    导入逻辑：
    - 根据 租户域名 + 字段组名称 + 字段名 进行匹配
    - 状态为"已删除"时，删除对应的字段或选项
    - 支持新增字段和选项
    """
    current_user = await AuthControl.is_authed(token)
    tenant_id = current_user.current_tenant_id if not is_superuser(current_user) else 0
    app_name = "autofill"  # 默认应用名

    if not base_file and not options_file:
        return Fail(code=400, msg="请至少上传一个CSV文件")

    success_count = 0
    delete_count = 0
    error_messages = []

    # 先处理基础字段信息
    if base_file and base_file.filename.endswith('.csv'):
        try:
            content = await base_file.read()
            content_str = content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content_str))

            for row in csv_reader:
                try:
                    field_id = (row.get('ID') or '').strip()
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
                        error_messages.append(f"跳过空字段名行")
                        continue

                    # 查找字段
                    field_spec = None
                    found_group = None
                    
                    # 优先使用唯一标识（租户域名+页面名称+字段组名称+字段名）查找
                    if not field_spec and tenant_domain and group_name:
                        field_spec, found_group = await _find_field_by_names(
                            tenant_domain, group_name, field_name, page_name,
                            tenant_id if not is_superuser(current_user) else None
                        )
                    
                    # 其次使用ID查找
                    if not field_spec and field_id:
                        field_query = Q(id=int(field_id))
                        if not is_superuser(current_user):
                            field_query &= Q(tenant_id=tenant_id)
                        field_spec = await field_spec_controller.model.filter(field_query).first()

                    # 最后仅使用字段名查找（兼容性）
                    if not field_spec and field_name:
                        field_query = Q(field_name=field_name)
                        if not is_superuser(current_user):
                            field_query &= Q(tenant_id=tenant_id)
                        field_spec = await field_spec_controller.model.filter(field_query).first()

                    # 解析corrections
                    corrections = []
                    if corrections_text:
                        for line in corrections_text.split('\n'):
                            line = line.strip()
                            if line.startswith('*'):
                                text = line[1:].strip()
                                if text:
                                    corrections.append({"text": text})

                    if field_spec:
                        # 更新现有字段
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
                        # 创建新字段
                        if status == '已删除':
                            continue

                        # 确定租户ID
                        target_tenant_id = tenant_id
                        if tenant_domain:
                            tenant = await Tenant.filter(domain=tenant_domain).first()
                            if tenant:
                                target_tenant_id = tenant.id

                        # 确定字段组ID
                        # 优先使用查找时找到的字段组
                        target_group_id = found_group.id if found_group else None
                        
                        # 如果没有找到字段组，尝试重新查找
                        if not target_group_id and group_name:
                            # 优先使用目标租户ID查找字段组
                            search_tenant_id = target_tenant_id if target_tenant_id > 0 else tenant_id
                            group_query = Q(group_name=group_name)
                            if search_tenant_id > 0:
                                group_query &= Q(tenant_id=search_tenant_id)
                            if page_name:
                                group_query &= Q(page_name=page_name)
                            
                            group = await FieldGroupConfig.filter(group_query).first()
                            if group:
                                target_group_id = group.id

                        # 准备选项配置
                        options = {}
                        if field_type in ['select_single', 'select_multi']:
                            options['items'] = []
                            if field_type == 'select_multi':
                                options['min_selections'] = 1
                                options['max_selections'] = 0

                        from app.schemas.fill_page import FieldSpecCreate, FieldOptions
                        spec_in = FieldSpecCreate(
                            field_name=field_name,
                            field_label=field_label or field_name,
                            field_type=field_type or 'text',
                            fill_instruction=fill_instruction,
                            field_group_ids=[target_group_id] if target_group_id else []
                        )

                        if options:
                            spec_in.options = FieldOptions(**options)

                        new_spec = await field_spec_controller.create_field_spec(
                            obj_in=spec_in,
                            tenant_id=target_tenant_id if target_tenant_id > 0 else tenant_id,
                            app_name=app_name
                        )

                        # 保存corrections
                        if corrections:
                            new_spec.corrections = corrections
                            await new_spec.save()

                        success_count += 1

                except Exception as e:
                    error_messages.append(f"处理基础字段行失败: {str(e)}")

        except Exception as e:
            error_messages.append(f"读取基础字段文件失败: {str(e)}")

    # 处理选项详情
    if options_file and options_file.filename.endswith('.csv'):
        try:
            content = await options_file.read()
            content_str = content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content_str))

            for row in csv_reader:
                try:
                    field_id = (row.get('字段ID') or '').strip()
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
                        error_messages.append(f"跳过缺少字段名或选项值的行")
                        continue

                    # 查找字段
                    field_spec = None
                    
                    # 优先使用唯一标识（租户域名+页面名称+字段组名称+字段名）查找
                    if not field_spec and tenant_domain and group_name:
                        field_spec, _ = await _find_field_by_names(
                            tenant_domain, group_name, field_name, page_name,
                            tenant_id if not is_superuser(current_user) else None
                        )
                    
                    # 其次使用ID查找
                    if not field_spec and field_id:
                        field_query = Q(id=int(field_id))
                        if not is_superuser(current_user):
                            field_query &= Q(tenant_id=tenant_id)
                        field_spec = await field_spec_controller.model.filter(field_query).first()

                    # 最后仅使用字段名查找（兼容性）
                    if not field_spec and field_name:
                        field_query = Q(field_name=field_name)
                        if not is_superuser(current_user):
                            field_query &= Q(tenant_id=tenant_id)
                        field_spec = await field_spec_controller.model.filter(field_query).first()

                    if not field_spec:
                        error_messages.append(f"字段 {field_name} 不存在，跳过")
                        continue

                    # 检查是否为删除操作
                    if status == '已删除':
                        options = field_spec.options or {}
                        items = options.get('items', [])
                        items = [item for item in items if str(item.get('value', '')) != option_value]
                        options['items'] = items
                        field_spec.options = options
                        await field_spec.save()
                        delete_count += 1
                        continue

                    # 解析corrections
                    corrections = []
                    if corrections_text:
                        for line in corrections_text.split('\n'):
                            line = line.strip()
                            if line.startswith('*'):
                                text = line[1:].strip()
                                if text:
                                    corrections.append({"text": text})

                    # 更新选项
                    options = field_spec.options or {}
                    items = options.get('items', [])

                    option_found = False
                    for item in items:
                        if str(item.get('value', '')) == option_value:
                            item['label'] = option_label
                            item['fill_instruction'] = fill_instruction
                            item['corrections'] = corrections
                            item['is_deleted'] = False
                            option_found = True
                            break

                    if not option_found:
                        items.append({
                            'value': option_value,
                            'label': option_label,
                            'fill_instruction': fill_instruction,
                            'corrections': corrections,
                            'is_deleted': False
                        })

                    options['items'] = items
                    field_spec.options = options
                    await field_spec.save()
                    success_count += 1

                except Exception as e:
                    error_messages.append(f"处理选项行失败: {str(e)}")

        except Exception as e:
            error_messages.append(f"读取选项文件失败: {str(e)}")

    result = {
        "success_count": success_count,
        "delete_count": delete_count,
        "errors": error_messages[:10]
    }

    if error_messages:
        result["error_count"] = len(error_messages)

    return Success(data=result)


async def _find_field_by_names(tenant_domain: str, group_name: str, field_name: str, page_name: str = None, tenant_id: int = None):
    """
    通过租户域名、页面名称、字段组名称、字段名查找字段
    这是导入导出使用的唯一标识组合
    """
    # 1. 查找租户
    tenant = await Tenant.filter(domain=tenant_domain).first()
    if not tenant:
        return None, None

    if tenant_id is not None and tenant.id != tenant_id:
        return None, None

    # 2. 构建字段组查询条件
    group_query = Q(group_name=group_name, tenant_id=tenant.id)
    if page_name:
        group_query &= Q(page_name=page_name)

    group = await FieldGroupConfig.filter(group_query).first()
    if not group:
        return None, None

    # 3. 查找字段组关联的字段
    relations = await FieldGroupFieldSpec.filter(
        field_group_id=group.id
    ).all()
    if not relations:
        return None, group

    field_ids = [r.field_spec_id for r in relations]

    # 4. 查找匹配的字段
    field_spec = await field_spec_controller.model.filter(
        id__in=field_ids,
        field_name=field_name,
        tenant_id=tenant.id
    ).first()

    return field_spec, group


@router.post("/field_spec/sync_options", summary="同步字段选项（根据OpenAPI Schema从API获取）")
async def sync_field_spec_options(
    sync_in: FieldSpecSyncOptionsRequest,
    token: str = Header(..., description="token验证"),
):
    """
    根据OpenAPI Schema配置从API同步下拉选项并保存到字段
    1. 验证必填字段
    2. 解析OpenAPI Schema获取接口信息
    3. 使用配置的Header请求API
    4. 使用jsonpath-ng解析数据
    5. 保存到数据库（新建或更新字段）
    """
    current_user = await AuthControl.is_authed(token)
    tenant_id = current_user.tenant_id if hasattr(current_user, 'tenant_id') else 0
    
    # 验证必填字段
    if not sync_in.field_name:
        return Fail(code=400, msg="字段名称不能为空")
    if not sync_in.field_label:
        return Fail(code=400, msg="字段标签不能为空")
    if not sync_in.field_group_ids:
        return Fail(code=400, msg="请至少选择一个关联字段组")
    if not sync_in.options.api_schema:
        return Fail(code=400, msg="请先配置OpenAPI Schema")
    
    try:
        # 解析YAML格式的Schema
        spec_dict = yaml.safe_load(sync_in.options.api_schema)
        
        # 获取服务器URL和路径
        servers = spec_dict.get('servers', [])
        base_url = servers[0].get('url', '') if servers else ''
        
        paths = spec_dict.get('paths', {})
        if not paths:
            return Fail(code=400, msg="Schema中未找到paths配置")
        
        # 获取第一个接口（支持GET或POST）
        api_path = None
        api_method = None
        api_config = None
        for path, methods in paths.items():
            if 'get' in methods:
                api_path = path
                api_method = 'get'
                api_config = methods['get']
                break
            elif 'post' in methods:
                api_path = path
                api_method = 'post'
                api_config = methods['post']
                break
        
        if not api_path:
            return Fail(code=400, msg="Schema中未找到GET或POST接口")
        
        # 构建完整URL
        full_url = base_url.rstrip('/') + api_path
        
        # 构建请求Headers
        headers = {}
        for header_item in sync_in.options.api_headers:
            if header_item.key and header_item.value:
                headers[header_item.key] = header_item.value
        
        # 从Schema中解析静态参数（x-api-params扩展字段）
        x_api_params = api_config.get('x-api-params') or spec_dict.get('x-api-params', {})
        
        # 使用异步HTTP客户端发送请求
        async with httpx.AsyncClient(timeout=30.0) as client:
            if api_method == 'get':
                response = await client.get(full_url, headers=headers, params=x_api_params)
            else:
                headers['Content-Type'] = 'application/json'
                response = await client.post(full_url, headers=headers, json=x_api_params)
            response.raise_for_status()
            response_data = response.json()
        
        # 获取字段映射配置（x-field-mapping扩展字段）
        x_field_mapping = api_config.get('x-field-mapping') or spec_dict.get('x-field-mapping', {})
        
        # 默认使用标准格式
        label_path = x_field_mapping.get('label_path', '$.data[*].label')
        value_path = x_field_mapping.get('value_path', '$.data[*].value')
        
        # 使用jsonpath-ng解析和提取数据
        try:
            label_expr = jsonpath_parse(label_path)
            label_results = [match.value for match in label_expr.find(response_data)]
            
            value_expr = jsonpath_parse(value_path)
            value_results = [match.value for match in value_expr.find(response_data)]
        except Exception as e:
            return Fail(code=400, msg=f"字段映射路径解析错误: {str(e)}")
        
        # 检查是否提取到数据
        if not label_results:
            return Fail(code=400, msg="API返回数据格式不正确，未找到选项列表")
        
        # 构建选项列表
        new_items = []
        for i, label in enumerate(label_results):
            value = value_results[i] if i < len(value_results) else label
            label = str(label) if label is not None else ''
            value = str(value) if value is not None else ''
            
            if not label:
                continue
            
            new_items.append({
                'value': value,
                'label': label,
                'fill_instruction': '',
                'corrections': [],
                'is_deleted': False
            })
        
        # 获取第一个字段组信息（用于获取app_name）
        # 超级用户(tenant_id=0)可以访问任何字段组
        if tenant_id > 0:
            field_group = await FieldGroupConfig.filter(
                id=sync_in.field_group_ids[0],
                tenant_id=tenant_id
            ).first()
        else:
            field_group = await FieldGroupConfig.filter(
                id=sync_in.field_group_ids[0]
            ).first()
        
        if not field_group:
            return Fail(code=400, msg="字段组不存在或无权限访问")
        
        app_name = field_group.app_name
        
        # 构建options数据
        options_data = {
            'items': new_items,
            'min_selections': sync_in.options.min_selections or 1,
            'max_selections': sync_in.options.max_selections or 0,
            'api_schema': sync_in.options.api_schema,
            'api_headers': [{'key': h.key, 'value': h.value} for h in (sync_in.options.api_headers or [])]
        }
        
        # 使用service层的upsert_field_spec方法
        # 同步选项时默认：只同步value（replace模式），删除接口返回中不存在的选项
        result = await upsert_field_spec(
            tenant_id=tenant_id,
            app_name=app_name,
            field_name=sync_in.field_name,
            field_label=sync_in.field_label,
            field_type=sync_in.field_type,
            field_group_ids=sync_in.field_group_ids,
            fill_instruction=sync_in.fill_instruction,
            options=options_data,
            sync_mode='replace',  # 只同步value，其他字段保持原样
            delete_not_exist=True  # 删除接口返回中不存在的选项
        )
        
        field_spec = result["field_spec"]
        updated_count = result["updated_count"]
        final_items = result["items"]

        return Success(data={
            "items": final_items,
            "updated_count": updated_count,
            "field_id": field_spec.id,
            "message": f"同步成功，共更新 {updated_count} 个选项"
        })
        
    except yaml.YAMLError as e:
        return Fail(code=400, msg=f"Schema YAML格式错误: {str(e)}")
    except httpx.HTTPError as e:
        return Fail(code=400, msg=f"请求API失败: {str(e)}")
    except Exception as e:
        return Fail(code=500, msg=f"同步失败: {str(e)}")
