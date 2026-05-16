"""
LLM Handler 业务服务层
将 llm_handlers.py 中的业务逻辑下沉到这里
"""
import json
from typing import Any, Dict, List, Optional, Tuple
from fastapi.exceptions import HTTPException
from tortoise.expressions import Q

from app.controllers.autofill import (
    field_group_config_controller,
    field_spec_controller,
    fill_page_controller,
)
from app.controllers.llm_config import llm_config_controller
from app.log import logger
from app.models.autofill import FieldGroupFieldSpec, FillPage
from app.services.autofill.field_group_query_service import field_group_query_service
from app.services.autofill.prompt_service import build_fields_instructions
from app.services.llm.llm_proxy_service import llm_proxy_service


class LLMFillDataService:
    """AI 填充数据服务"""
    
    @staticmethod
    async def get_fill_data(
        tenant_id: int,
        app_name: str,
        session_id: str,
        data: Dict,
        page_name: str = "",
        response_mode: str = "sync"
    ) -> Dict[str, Any]:
        """获取 AI 填充数据"""
        from app.services.autofill.ai_fill_service import get_ai_fill_service
        
        dify_url = ""
        dify_api_key = ""
        
        if page_name:
            page = await FillPage.filter(
                tenant_id=tenant_id,
                page_name=page_name,
                is_active=True
            ).first()
            if page and page.dify_agent_url and page.dify_api_key:
                dify_url = page.dify_agent_url
                dify_api_key = page.dify_api_key
        
        if not dify_url or not dify_api_key:
            raise HTTPException(status_code=500, detail="Dify configuration not found")
        
        service = get_ai_fill_service()
        
        if response_mode == "async":
            result = await service.process_async(
                session_id=session_id,
                tenant_id=tenant_id,
                app_name=app_name,
                data=data,
                dify_url=dify_url,
                dify_api_key=dify_api_key
            )
        else:
            result = await service.process_sync(
                session_id=session_id,
                tenant_id=tenant_id,
                app_name=app_name,
                data=data,
                dify_url=dify_url,
                dify_api_key=dify_api_key
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
        page_name: str,
        field_names: List[str] = None,
        group_names: List[str] = None
    ) -> Dict[str, Any]:
        """获取字段组 Schema 信息"""
        field_names_filter = set(field_names or [])
        group_names_filter = set(group_names or [])
        
        page = await fill_page_controller.model.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            page_name=page_name
        ).first()
        
        if not page:
            return {"fields": [], "merged_config": {}, "prompt_info": {}, "function_calling": {}}
        
        if group_names_filter:
            field_groups = await field_group_config_controller.model.filter(
                tenant_id=tenant_id,
                app_name=app_name,
                page_id=page.id,
                group_name__in=list(group_names_filter)
            ).all()
        else:
            field_groups = await field_group_config_controller.model.filter(
                tenant_id=tenant_id,
                app_name=app_name,
                page_id=page.id,
                group_name="default"
            ).all()
        
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
        
        merged_config = FieldGroupSchemaService._merge_field_groups_config(field_groups)
        template_base = merged_config.get("prompt_template_base") or """你是一个智能填单助手。请根据输入内容，提取指定字段的信息。

需要提取的字段：
{{fields_instructions}}

请严格按照字段要求提取信息，并以JSON格式返回结果。"""
        
        function_schema = FieldGroupSchemaService._build_function_schema(field_specs)
        
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
    
    @staticmethod
    def _build_function_schema(field_specs: List) -> Dict[str, Any]:
        """构建 Function Calling Schema"""
        function_schema = {
            "type": "function",
            "function": {
                "name": "fill_form",
                "description": "从对话中提取表单数据",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        for fs in field_specs:
            param_info = FieldGroupSchemaService._build_field_param(fs)
            function_schema["function"]["parameters"]["properties"][fs.field_name] = param_info
            function_schema["function"]["parameters"]["required"].append(fs.field_name)
        
        return function_schema
    
    @staticmethod
    def _build_field_param(field_spec) -> Dict[str, Any]:
        """构建单个字段的参数定义"""
        description = field_spec.fill_instruction or field_spec.field_label or field_spec.field_name
        
        param_info = {"type": "string", "description": description}
        
        if field_spec.options and field_spec.options.get("items"):
            items = field_spec.options.get("items", [])
            valid_items = [item for item in items if not item.get("is_deleted", False)]
            if valid_items:
                param_info["enum"] = [item.get("label") for item in valid_items if item.get("label")]
                
                option_descs = []
                for item in valid_items[:10]:
                    label = item.get("label", "")
                    fill_inst = item.get("fill_instruction", "")
                    if fill_inst:
                        option_descs.append(f"{label}: {fill_inst}")
                    else:
                        option_descs.append(label)
                
                if option_descs:
                    param_info["description"] = f"{description}。可选值：{', '.join(option_descs)}"
                    if len(valid_items) > 10:
                        param_info["description"] += f" 等共{len(valid_items)}个选项"
        
        return param_info


llm_fill_data_service = LLMFillDataService()
field_group_schema_service = FieldGroupSchemaService()
