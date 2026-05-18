"""
字段规格服务层
提供字段的创建、更新、同步等核心逻辑
"""
from typing import Dict, List, Optional, Any, Tuple

from tortoise.expressions import Q

from app.models.autofill import FieldGroupFieldSpec, FieldGroupConfig, FieldSpec
from app.models.admin import Tenant


async def find_field_by_unique_key(
    tenant_domain: str,
    page_name: str,
    group_name: str,
    field_name: str,
    tenant_id: Optional[int] = None,
) -> Tuple[Optional[FieldSpec], Optional[FieldGroupConfig]]:
    """
    根据唯一标识组合查找字段
    
    唯一标识：租户域名 + 页面名称 + 字段组名称 + 字段名
    
    Args:
        tenant_domain: 租户域名
        page_name: 页面名称
        group_name: 字段组名称
        field_name: 字段名
        tenant_id: 可选的租户ID限制（用于非超级用户）
    
    Returns:
        Tuple[字段对象, 字段组对象] 如果未找到则返回 (None, None)
    """
    # 1. 查找租户
    tenant = await Tenant.filter(domain=tenant_domain).first()
    if not tenant:
        return None, None
    
    # 检查租户ID限制
    if tenant_id is not None and tenant.id != tenant_id:
        return None, None
    
    # 2. 查找字段组（支持页面名称过滤）
    group_query = Q(group_name=group_name, tenant_id=tenant.id)
    if page_name:
        group_query &= Q(page_name=page_name)
    
    group = await FieldGroupConfig.filter(group_query).first()
    if not group:
        return None, None
    
    # 3. 查找字段组关联的所有字段ID
    relations = await FieldGroupFieldSpec.filter(
        field_group_id=group.id
    ).all()
    if not relations:
        return None, group
    
    field_ids = [r.field_spec_id for r in relations]
    
    # 4. 在关联的字段中查找匹配的字段名
    field_query = Q(id__in=field_ids, field_name=field_name)
    if tenant_id is not None:
        field_query &= Q(tenant_id=tenant.id)
    
    field_spec = await FieldSpec.filter(field_query).first()
    
    return field_spec, group


async def upsert_field_spec(
    tenant_id: int,
    app_name: str,
    field_name: str,
    field_label: str,
    field_type: str,
    field_group_ids: List[int],
    fill_instruction: str = "",
    options: Optional[Dict[str, Any]] = None,
    delete_not_exist: bool = True,
    sync_mode: str = "merge",
) -> Dict[str, Any]:
    """
    创建或更新字段规格

    Args:
        tenant_id: 租户ID
        app_name: 应用名称
        field_name: 字段名称
        field_label: 字段标签
        field_type: 字段类型
        field_group_ids: 关联字段组ID列表
        fill_instruction: 填写指引
        options: 选项配置
        delete_not_exist: 是否删除接口返回中不存在的选项
        sync_mode: 同步模式，仅支持merge=合并（新值非空时更新，否则保留原值），保留参数用于后续扩展

    Returns:
        Dict包含: field_spec(字段对象), is_new(是否新建), updated_count(更新选项数)
    """
    # 查找现有字段 - 直接操作 model，不通过 controller
    field_spec = await FieldSpec.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        field_name=field_name
    ).first()
    
    # 处理options
    if options is None:
        options = {}
    
    # 确保options包含必要的默认值
    options_data = {
        'items': options.get('items', []),
        'min_selections': options.get('min_selections', 1),
        'max_selections': options.get('max_selections', 0),
    }
    
    # 保留api_schema和api_headers（如果存在）
    if 'api_schema' in options:
        options_data['api_schema'] = options['api_schema']
    if 'api_headers' in options:
        options_data['api_headers'] = options['api_headers']
    
    if field_spec:
        # 字段已存在，使用merge模式处理选项
        existing_options = field_spec.options or {}
        existing_items = existing_options.get('items', []) if isinstance(existing_options, dict) else []
        new_items = options_data['items']

        # merge模式（默认）：合并现有选项和新选项，新值非空时更新，否则保留原值
        merged_items_map = {}
        for item in existing_items:
            if isinstance(item, dict) and 'label' in item:
                merged_items_map[item['label']] = item

        for new_item in new_items:
            label = new_item['label']
            if label in merged_items_map:
                # 新值非空时更新，否则保留原值
                for key in ['value', 'label', 'fill_instruction', 'corrections']:
                    if new_item.get(key):
                        merged_items_map[label][key] = new_item[key]
            else:
                merged_items_map[label] = new_item

        final_items = list(merged_items_map.values())

        # 如果开启delete_not_exist，删除接口返回中不存在的选项
        if delete_not_exist:
            new_item_labels = {item['label'] for item in new_items}
            final_items = [item for item in final_items if item['label'] in new_item_labels]
        
        options_data['items'] = final_items
        
        # 获取当前所有关联的字段组ID
        existing_relations = await FieldGroupFieldSpec.filter(field_spec_id=field_spec.id).all()
        existing_group_ids = [r.field_group_id for r in existing_relations]
        
        # 合并字段组ID（去重）
        all_group_ids = list(set(existing_group_ids + field_group_ids))
        
        # 更新字段 - 直接操作 model
        field_spec.field_label = field_label
        field_spec.field_type = field_type
        field_spec.fill_instruction = fill_instruction
        field_spec.options = options_data
        await field_spec.save()

        # 确保字段与所有字段组建立关联
        for group_id in field_group_ids:
            existing_relation = await FieldGroupFieldSpec.filter(
                field_group_id=group_id,
                field_spec_id=field_spec.id,
                tenant_id=tenant_id
            ).first()

            if not existing_relation:
                await FieldGroupFieldSpec.create(
                    field_group_id=group_id,
                    field_spec_id=field_spec.id,
                    tenant_id=tenant_id,
                    app_name=app_name
                )

        return {
            "field_spec": field_spec,
            "is_new": False,
            "updated_count": len(new_items),
            "items": final_items
        }
    else:
        # 字段不存在，创建新字段 - 直接操作 model
        field_spec = await FieldSpec.create(
            tenant_id=tenant_id,
            app_name=app_name,
            field_name=field_name,
            field_label=field_label,
            field_type=field_type,
            fill_instruction=fill_instruction,
            options=options_data
        )

        # 创建字段组关联
        for group_id in field_group_ids:
            await FieldGroupFieldSpec.create(
                field_group_id=group_id,
                field_spec_id=field_spec.id,
                tenant_id=tenant_id,
                app_name=app_name
            )

        return {
            "field_spec": field_spec,
            "is_new": True,
            "updated_count": len(options_data['items']),
            "items": options_data['items']
        }
