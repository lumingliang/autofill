"""
LLM Handler 业务服务层
将 llm_handlers.py 中的业务逻辑下沉到这里
"""
import json
from typing import Any, Dict, List, Optional
from fastapi.exceptions import HTTPException

from app.controllers.autofill import (
    field_group_config_controller,
    field_spec_controller,
)
from app.controllers.llm_config import llm_config_controller
from app.log import logger
from app.models.autofill import FieldGroupFieldSpec
from app.services.autofill.field_group_query_service import field_group_query_service
from app.services.autofill.prompt_service import build_fields_instructions
from app.services.llm.structured_output.schema_builder import FCSchemaBuilder
from app.services.llm.llm_proxy_service import llm_proxy_service


class LLMFillDataService:
    """AI 填充数据服务"""
    
    @staticmethod
    async def get_fill_data(
        tenant_id: int,
        app_name: str,
        session_id: str,
        data: Dict,
        response_mode: str = "sync"
    ) -> Dict[str, Any]:
        """获取 AI 填充数据"""
        from app.services.autofill.ai_fill_service import get_ai_fill_service
        
        service = get_ai_fill_service()
        
        if response_mode == "async":
            result = await service.process_async(
                session_id=session_id,
                tenant_id=tenant_id,
                app_name=app_name,
                data=data
            )
        else:
            result = await service.process_sync(
                session_id=session_id,
                tenant_id=tenant_id,
                app_name=app_name,
                data=data
            )
        
        return result
    
    @staticmethod
    async def get_fill_result(tenant_id: int, app_name: str, session_id: str) -> Optional[Dict[str, Any]]:
        """获取填充结果"""
        from app.services.autofill.ai_fill_service import get_ai_fill_service
        
        service = get_ai_fill_service()
        return await service.get_result(
            session_id=session_id,
            tenant_id=tenant_id,
            app_name=app_name
        )


class FieldGroupSchemaService:
    """字段组 Schema 服务"""
    
    @staticmethod
    async def get_field_groups_schema(
        tenant_id: int,
        app_name: str,
        field_names: List[str] = None,
        group_names: List[str] = None
    ) -> Dict[str, Any]:
        """获取字段组 Schema 信息"""
        field_names_filter = set(field_names or [])
        group_names_filter = set(group_names or [])
        
        # 构建字段组查询
        group_query = field_group_config_controller.model.filter(
            tenant_id=tenant_id,
            app_name=app_name
        )
        
        if group_names_filter:
            group_query = group_query.filter(group_name__in=list(group_names_filter))
        
        field_groups = await group_query.all()
        
        if not field_groups:
            return {"fields": [], "merged_config": {}, "prompt_info": {}, "function_calling": {}}
        
        field_group_ids = [fg.id for fg in field_groups]
        relations_query = FieldGroupFieldSpec.filter(
            field_group_id__in=field_group_ids,
            tenant_id=tenant_id,
            app_name=app_name
        )
        
        if field_names_filter:
            matching_specs = await field_spec_controller.model.filter(
                tenant_id=tenant_id,
                app_name=app_name,
                field_name__in=list(field_names_filter),
                is_active=True
            ).all()
            matching_spec_ids = [fs.id for fs in matching_specs]
            relations_query = relations_query.filter(field_spec_id__in=matching_spec_ids)
        
        relations = await relations_query.all()
        field_spec_ids = list(set([r.field_spec_id for r in relations]))
        
        if not field_spec_ids:
            return {"fields": [], "merged_config": {}, "prompt_info": {}, "function_calling": {}}
        
        field_specs = await field_spec_controller.model.filter(
            id__in=field_spec_ids,
            is_active=True
        ).all()
        
        if not field_specs:
            return {"fields": [], "merged_config": {}, "prompt_info": {}, "function_calling": {}}
        
        from app.services.autofill.constants import DEFAULT_PROMPT_TEMPLATE_BASE
        merged_config = FieldGroupSchemaService._merge_field_groups_config(field_groups)
        template_base = merged_config.get("prompt_template_base") or DEFAULT_PROMPT_TEMPLATE_BASE
        
        # 转换 field_specs 为 db_fields 格式
        db_fields = [
            {
                "field_name": fs.field_name,
                "field_label": fs.field_label,
                "field_type": fs.field_type.value if hasattr(fs.field_type, 'value') else fs.field_type,
                "fill_instruction": fs.fill_instruction,
                "options": fs.options,
                "corrections": fs.corrections,
            }
            for fs in field_specs
        ]
        function_schema = FCSchemaBuilder.build_fc_tools(
            db_fields,
            function_name="fill_form",
            description="从对话中提取表单数据"
        )

        return {
            "fields": [
                {
                    "id": fs.id,
                    "field_name": fs.field_name,
                    "field_label": fs.field_label,
                    "field_type": fs.field_type,
                    "fill_instruction": fs.fill_instruction,
                    "options": fs.options,
                    "corrections": fs.corrections,
                    "is_active": fs.is_active,
                }
                for fs in field_specs
            ],
            "merged_config": merged_config,
            "prompt_info": {"template_base": template_base},
            "function_calling": {
                "schema": function_schema,
                "json_schema": json.dumps(function_schema, ensure_ascii=False, indent=2),
            }
        }
    
    @staticmethod
    def _merge_field_groups_config(field_groups: List) -> Dict[str, Any]:
        """合并多个字段组的配置"""
        merged = {
            "prompt_template_base": "",
            "output_templates": {},
            "description": ""
        }
        
        descriptions = []
        for fg in field_groups:
            if not merged["prompt_template_base"] and fg.prompt_template_base:
                merged["prompt_template_base"] = fg.prompt_template_base
            
            if fg.output_templates:
                merged["output_templates"].update(fg.output_templates)
            
            if fg.description:
                descriptions.append(fg.description)
        
        if descriptions:
            merged["description"] = "; ".join(descriptions)
        
        return merged


llm_fill_data_service = LLMFillDataService()
field_group_schema_service = FieldGroupSchemaService()
