# 这个文件用于替换原有的导入函数
# 由于原文件代码结构混乱，这里提供完整的修复版本

import csv
import io
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Header, Query, UploadFile
from fastapi.exceptions import HTTPException
from pydantic import BaseModel, Field
from tortoise.expressions import Q

from app.controllers.autofill import (
    field_group_config_controller,
    field_spec_controller,
    fill_page_controller,
)
from app.core.auth import AuthControl
from app.models.autofill import (
    FieldGroupConfig,
    FieldGroupFieldSpec,
    FieldSpec,
    FillPage,
    Tenant,
)
from app.schemas.base import Fail, Success
from app.schemas.fill_page import FieldSpecCreate, FieldSpecUpdate
from app.core.auth import is_superuser

router = APIRouter()


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
                    field_id = row.get('ID', '').strip()
                    field_name = row.get('字段名', '').strip()
                    field_label = row.get('字段标签', '').strip()
                    field_type = row.get('字段类型', '').strip()
                    fill_instruction = row.get('填写指引', '').strip()
                    corrections_text = row.get('corrections', '').strip()
                    status = row.get('状态', '').strip()
                    tenant_domain = row.get('租户域名', '').strip()
                    group_name = row.get('字段组名称', '').strip()
                    page_name = row.get('页面名称', '').strip()

                    if not field_name:
                        error_messages.append(f"跳过空字段名行")
                        continue

                    # 查找字段
                    field_spec = None
                    if field_id:
                        field_query = Q(id=int(field_id))
                        if not is_superuser(current_user):
                            field_query &= Q(tenant_id=tenant_id)
                        field_spec = await field_spec_controller.model.filter(field_query).first()

                    if not field_spec and tenant_domain and group_name:
                        field_spec = await _find_field_by_names(
                            tenant_domain, group_name, field_name,
                            tenant_id if not is_superuser(current_user) else None
                        )

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
                        target_group_id = None
                        if group_name:
                            if target_tenant_id > 0:
                                group = await FieldGroupConfig.filter(
                                    group_name=group_name,
                                    tenant_id=target_tenant_id
                                ).first()
                            else:
                                group = await FieldGroupConfig.filter(group_name=group_name).first()
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
                    field_id = row.get('字段ID', '').strip()
                    field_name = row.get('字段名', '').strip()
                    option_value = row.get('选项值', '').strip()
                    option_label = row.get('选项标签', '').strip()
                    fill_instruction = row.get('填写说明', '').strip()
                    corrections_text = row.get('corrections', '').strip()
                    status = row.get('状态', '').strip()
                    tenant_domain = row.get('租户域名', '').strip()
                    group_name = row.get('字段组名称', '').strip()

                    if not field_name or not option_value:
                        error_messages.append(f"跳过缺少字段名或选项值的行")
                        continue

                    # 查找字段
                    field_spec = None
                    if field_id:
                        field_query = Q(id=int(field_id))
                        if not is_superuser(current_user):
                            field_query &= Q(tenant_id=tenant_id)
                        field_spec = await field_spec_controller.model.filter(field_query).first()

                    if not field_spec and tenant_domain and group_name:
                        field_spec = await _find_field_by_names(
                            tenant_domain, group_name, field_name,
                            tenant_id if not is_superuser(current_user) else None
                        )

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


async def _find_field_by_names(tenant_domain: str, group_name: str, field_name: str, tenant_id: int = None):
    """
    通过租户域名、字段组名称、字段名查找字段
    """
    tenant = await Tenant.filter(domain=tenant_domain).first()
    if not tenant:
        return None

    if tenant_id is not None and tenant.id != tenant_id:
        return None

    group = await FieldGroupConfig.filter(
        group_name=group_name,
        tenant_id=tenant.id
    ).first()
    if not group:
        return None

    relations = await FieldGroupFieldSpec.filter(
        field_group_id=group.id
    ).all()
    if not relations:
        return None

    field_ids = [r.field_spec_id for r in relations]

    field_spec = await field_spec_controller.model.filter(
        id__in=field_ids,
        field_name=field_name,
        tenant_id=tenant.id
    ).first()

    return field_spec
