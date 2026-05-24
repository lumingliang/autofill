"""
字段规格服务层
提供字段的创建、更新、同步等核心逻辑
"""
import logging
from typing import Dict, List, Optional, Any

from app.models.autofill import FieldGroupFieldSpec, FieldSpec, FieldGroupConfig

logger = logging.getLogger(__name__)


async def upsert_field_spec(
    tenant_id: int,
    app_name: str,
    field_name: str,
    field_label: str,
    field_type: str,
    fill_instruction: str = "",
    options: Optional[Dict[str, Any]] = None,
    delete_not_exist: bool = True,
    sync_mode: str = "merge",
    field_group_id: int = 0,
) -> Dict[str, Any]:
    """
    创建或更新字段规格

    Args:
        tenant_id: 租户ID
        app_name: 应用名称
        field_name: 字段名称
        field_label: 字段标签
        field_type: 字段类型
        fill_instruction: 填写指引
        options: 选项配置
        delete_not_exist: 是否删除接口返回中不存在的选项
        sync_mode: 同步模式，仅支持merge=合并（新值非空时更新，否则保留原值），保留参数用于后续扩展
        field_group_id: 关联字段组ID，可选。如果为0，则使用app_name下的default字段组

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
                for key in ['value', 'label', 'fill_instruction']:
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

        # 更新字段 - 直接操作 model
        field_spec.field_label = field_label
        field_spec.field_type = field_type
        field_spec.fill_instruction = fill_instruction
        field_spec.options = options_data
        
        await field_spec.save()

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

        # 如果没有指定字段组ID，使用app_name下的default字段组
        if field_group_id == 0:
            field_group_id = await get_or_create_default_field_group(tenant_id, app_name)

        # 如果指定了字段组ID，创建字段组关联
        if field_group_id > 0:
            group = await FieldGroupConfig.filter(id=field_group_id).first()
            if group:
                await FieldGroupFieldSpec.create(
                    field_group_id=field_group_id,
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
