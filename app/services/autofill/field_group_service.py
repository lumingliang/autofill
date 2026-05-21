"""
字段组服务（统一处理字段组 CRUD 和关联关系）
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi.exceptions import HTTPException

logger = logging.getLogger(__name__)

from app.controllers.autofill import (
    field_group_config_controller,
    field_spec_controller,
)
from app.models.autofill import (
    FieldGroupFieldSpec,
    FieldType,
    generate_field_group_code
)
from app.schemas.fill_page import OutputTemplateItem, FieldGroupConfigCreate
from app.services.autofill.field_spec_service import upsert_field_spec
from app.services.autofill.constants import DEFAULT_PROMPT_TEMPLATE_BASE


class FieldGroupService:
    """字段组服务"""
    
    @staticmethod
    async def upsert_field_group(
        tenant_id: int,
        app_name: str,
        group_name: str,
        group_code: Optional[str] = None,
        output_templates: Optional[Dict] = None,
        prompt_template_base: Optional[str] = None,
        fields: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        创建或更新字段组，并批量处理字段列表
        
        - 如果字段组不存在，自动创建
        - 遍历字段列表：字段不存在则创建并添加关联，存在则只添加关联关系
        """
        
        # 1. 查询或创建字段组
        field_group = await field_group_config_controller.model.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            group_name=group_name
        ).first()
        
        if field_group:
            # 更新字段组
            update_data = {}
            if output_templates is not None:
                update_data["output_templates"] = output_templates
            if prompt_template_base is not None:
                update_data["prompt_template_base"] = prompt_template_base
            if update_data:
                update_data["version"] = field_group.version + 1
                await field_group_config_controller.update(id=field_group.id, obj_in=update_data)
                field_group = await field_group_config_controller.get(id=field_group.id)
        else:
            # 创建新字段组
            code = group_code or generate_field_group_code()
            templates = output_templates or {}
            
            formatted_templates = {}
            for key, value in templates.items():
                if isinstance(value, dict):
                    formatted_templates[key] = OutputTemplateItem(**value)
                else:
                    formatted_templates[key] = OutputTemplateItem(template=value, description="")
            
            create_data = FieldGroupConfigCreate(
                group_name=group_name,
                group_code=code,
                app_name=app_name,
                tenant_id=tenant_id,
                output_templates=formatted_templates,
                prompt_template_base=prompt_template_base or DEFAULT_PROMPT_TEMPLATE_BASE
            )
            field_group = await field_group_config_controller.create_field_group(obj_in=create_data)
        
        # 2. 处理字段
        processed_fields = []
        fields_list = fields or []
        
        for field_item in fields_list:
            field_name = field_item.get("field_name")
            if not field_name:
                logger.warning(f"[FieldGroupService] 字段项缺少 field_name，跳过: {field_item}")
                continue
            field_label = field_item.get("field_label") or field_name
            field_type = field_item.get("field_type", "text")
            fill_instruction = field_item.get("fill_instruction") or ""
            options = field_item.get("options", {})
            
            # 使用枚举验证和转换 field_type
            field_type = FieldType(field_type) if field_type in [ft.value for ft in FieldType] else FieldType.TEXT

            # 使用 service 层统一处理
            result = await upsert_field_spec(
                tenant_id=tenant_id,
                app_name=app_name,
                field_name=field_name,
                field_label=field_label,
                field_type=field_type,
                fill_instruction=fill_instruction,
                options=options
            )

            field_spec = result["field_spec"]
            is_new = result["is_new"]

            # 创建字段组与字段的关联关系
            existing_relation = await FieldGroupFieldSpec.filter(
                field_group_id=field_group.id,
                field_spec_id=field_spec.id
            ).first()
            if not existing_relation:
                await FieldGroupFieldSpec.create(
                    field_group_id=field_group.id,
                    field_spec_id=field_spec.id,
                    tenant_id=tenant_id,
                    app_name=app_name
                )

            # 获取字段关联的所有字段组
            relations = await FieldGroupFieldSpec.filter(field_spec_id=field_spec.id).all()
            group_ids = [r.field_group_id for r in relations]
            
            processed_fields.append({
                "id": field_spec.id,
                "field_name": field_spec.field_name,
                "field_label": field_spec.field_label,
                "field_type": field_type,
                "field_group_ids": group_ids,
                "is_new": is_new
            })
        
        return {
            "id": field_group.id,
            "group_name": field_group.group_name,
            "group_code": field_group.group_code,
            "app_name": field_group.app_name,
            "output_templates": field_group.output_templates,
            "version": field_group.version,
            "fields": processed_fields,
            "field_count": len(processed_fields)
        }
    
    @staticmethod
    async def list_field_specs(
        tenant_id: int,
        app_name: str,
        group_names: Optional[List[str]] = None,
        field_names: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        查询字段明细列表
        
        - 支持通过 group_names 查询多个字段组
        - 支持通过 field_names 筛选指定字段
        """
        
        # 1. 查询字段组
        q = field_group_config_controller.model.filter(tenant_id=tenant_id, app_name=app_name)
        if group_names:
            q = q.filter(group_name__in=group_names)
        
        field_groups = await q.all()
        if not field_groups:
            return []
        
        # 2. 查询关联关系
        field_group_ids = [fg.id for fg in field_groups]
        relations = await FieldGroupFieldSpec.filter(
            field_group_id__in=field_group_ids,
            tenant_id=tenant_id,
            app_name=app_name
        ).all()
        
        field_spec_ids = list(set([r.field_spec_id for r in relations]))
        if not field_spec_ids:
            return []
        
        # 3. 查询字段
        q_spec = field_spec_controller.model.filter(id__in=field_spec_ids, is_active=True)
        if field_names:
            q_spec = q_spec.filter(field_name__in=field_names)
        
        field_specs = await q_spec.all()
        
        # 4. 组装结果
        result = []
        for fs in field_specs:
            relations_fs = await FieldGroupFieldSpec.filter(field_spec_id=fs.id).all()
            group_ids_fs = [r.field_group_id for r in relations_fs]
            
            groups_fs = await field_group_config_controller.model.filter(id__in=group_ids_fs).all()
            group_info = [
                {"id": g.id, "group_name": g.group_name, "group_code": g.group_code} 
                for g in groups_fs
            ]
            
            result.append({
                "id": fs.id,
                "field_name": fs.field_name,
                "field_label": fs.field_label,
                "field_type": fs.field_type,
                "fill_instruction": fs.fill_instruction,
                "options": fs.options,
                "corrections": fs.corrections,
                "is_active": fs.is_active,
                "field_groups": group_info
            })
        
        return result


field_group_service = FieldGroupService()
