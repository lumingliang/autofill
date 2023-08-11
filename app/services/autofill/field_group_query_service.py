"""
字段组查询服务（原 fetch_field_groups 从 handler 下沉）
"""
import json
from typing import Any, Dict, List, Optional, Set, Tuple

from app.controllers.autofill import (
    field_group_config_controller,
    field_spec_controller,
    fill_page_controller,
)
from app.models.autofill import FieldGroupFieldSpec
from app.services.llm.structured_output.schema_builder import FCSchemaBuilder


class FieldGroupQueryService:
    """字段组查询服务"""
    
    @staticmethod
    async def fetch_field_groups(
        tenant_id: int,
        app_name: str,
        page_name: str,
        group_fields: Dict[str, List[str]] = None,
        additional_data: Dict[str, Any] = None,
        use_additional_data: bool = False,
        include_reason: bool = False
    ) -> Dict[str, Any]:
        """
        查询字段组配置核心业务逻辑
        
        设计说明：
        - 字段的唯一索引是 field_name + tenant_id + app_name
        - FieldGroupFieldSpec 仅用于管理字段组和字段的映射关系
        - 查询策略分为两种情况：
          1. 指定了字段名：直接用 field_name + tenant_id + app_name 查询字段明细
          2. 未指定字段名：通过 field_group_id 查中间表获取 field_spec_id，再查字段明细
        """
        group_fields = group_fields or {}
        group_names = list(group_fields.keys())
        
        # 参数验证
        if not page_name:
            raise ValueError("page_name 不能为空")
        if not tenant_id or not app_name:
            raise ValueError("tenant_id 和 app_name 不能为空")
        
        # 1. 查询页面
        page = await fill_page_controller.model.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            page_name=page_name
        ).first()
        
        if not page:
            raise ValueError(f"页面 '{page_name}' 不存在 (tenant_id={tenant_id}, app_name={app_name})")
        
        # 2. 查询字段组
        q = field_group_config_controller.model.filter(tenant_id=tenant_id, app_name=app_name, page_id=page.id)
        if group_names:
            q = q.filter(group_name__in=group_names)
        
        field_groups = await q.all()
        
        if not field_groups:
            return {
                "page_name": page_name,
                "field_groups": [],
                "all_field_specs": [],
                "unified_function_schema": None,
                "combined_prompt": "",
            }
        
        # 3. 批量查询策略
        (
            all_field_specs_map, 
            group_to_spec_ids, 
            group_query_info
        ) = await FieldGroupQueryService._batch_query_fields(
            field_groups,
            group_fields,
            tenant_id,
            app_name
        )
        
        # 4. 组装结果
        return await FieldGroupQueryService._assemble_result(
            field_groups,
            all_field_specs_map,
            group_to_spec_ids,
            group_query_info,
            additional_data,
            use_additional_data,
            include_reason,
            page,
            page_name
        )
    
    @staticmethod
    async def _batch_query_fields(
        field_groups: List,
        group_fields: Dict[str, List[str]],
        tenant_id: int,
        app_name: str
    ) -> Tuple[Dict, Dict, Dict]:
        """批量查询字段策略"""
        
        # 1. 收集查询条件
        group_query_info = {}
        all_specified_field_names = set()
        all_full_fetch_group_ids = []
        
        for fg in field_groups:
            group_field_names = group_fields.get(fg.group_name) if group_fields else None
            
            if group_field_names:
                all_specified_field_names.update(group_field_names)
                group_query_info[fg.id] = {
                    "type": "specified", 
                    "field_names": set(group_field_names)
                }
            else:
                all_full_fetch_group_ids.append(fg.id)
                group_query_info[fg.id] = {"type": "full"}
        
        # 2. 批量查询字段
        all_field_specs_map = {}
        
        # 策略1：通过 field_name 批量查询
        if all_specified_field_names:
            specified_fields = await field_spec_controller.model.filter(
                tenant_id=tenant_id,
                app_name=app_name,
                field_name__in=list(all_specified_field_names),
                is_active=True
            ).all()
            for fs in specified_fields:
                all_field_specs_map[fs.field_name] = fs
        
        # 策略2：通过 field_group_id 批量查询
        group_to_spec_ids = {}
        if all_full_fetch_group_ids:
            relations = await FieldGroupFieldSpec.filter(
                field_group_id__in=all_full_fetch_group_ids,
                tenant_id=tenant_id,
                app_name=app_name
            ).all()
            
            for r in relations:
                if r.field_group_id not in group_to_spec_ids:
                    group_to_spec_ids[r.field_group_id] = []
                group_to_spec_ids[r.field_group_id].append(r.field_spec_id)
            
            all_spec_ids = [sid for ids in group_to_spec_ids.values() for sid in ids]
            if all_spec_ids:
                full_fetch_fields = await field_spec_controller.model.filter(
                    id__in=all_spec_ids,
                    tenant_id=tenant_id,
                    app_name=app_name,
                    is_active=True
                ).all()
                for fs in full_fetch_fields:
                    all_field_specs_map[fs.field_name] = fs
        
        return all_field_specs_map, group_to_spec_ids, group_query_info
    
    @staticmethod
    async def _assemble_result(
        field_groups: List,
        all_field_specs_map: Dict,
        group_to_spec_ids: Dict,
        group_query_info: Dict,
        additional_data: Dict[str, Any],
        use_additional_data: bool,
        include_reason: bool,
        page,
        page_name: str
    ) -> Dict[str, Any]:
        """组装结果返回"""

        field_groups_result = []
        all_db_fields = []  # 收集所有字段用于生成统一 schema
        system_prompts = []

        additional_field_names = set(additional_data.keys()) if use_additional_data and additional_data else set()

        # 第一步：收集所有字段组和字段信息
        for fg in field_groups:
            query_info = group_query_info.get(fg.id, {})
            query_type = query_info.get("type", "full")

            # 获取字段列表
            if query_type == "specified":
                target_names = query_info.get("field_names", set())
                field_specs = [
                    all_field_specs_map[name]
                    for name in target_names
                    if name in all_field_specs_map
                ]
                if not field_specs:
                    continue
            else:
                spec_ids = set(group_to_spec_ids.get(fg.id, []))
                field_specs = [
                    fs for fs in all_field_specs_map.values()
                    if fs.id in spec_ids
                ]

            # 使用附加数据过滤
            if use_additional_data and additional_field_names:
                field_specs = [fs for fs in field_specs if fs.field_name not in additional_field_names]
                if not field_specs:
                    continue

            # 转换 field_specs 为 db_fields 格式并收集
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
            all_db_fields.extend(db_fields)

            if fg.prompt_template_base and not system_prompts:
                system_prompts.append(fg.prompt_template_base)

            field_groups_result.append({
                "id": fg.id,
                "group_name": fg.group_name,
                "group_code": fg.group_code,
                "page_id": fg.page_id,
                "page_name": page.page_name if page else "",
                "prompt_template_base": fg.prompt_template_base,
                "output_templates": fg.output_templates or {},
                "version": fg.version,
                "is_active": fg.is_active,
                "description": fg.description,
                "field_specs": [
                    {
                        "id": fs.id,
                        "field_name": fs.field_name,
                        "field_label": fs.field_label,
                        "field_type": fs.field_type.value if hasattr(fs.field_type, 'value') else str(fs.field_type),
                        "fill_instruction": fs.fill_instruction,
                        "options": fs.options,
                        "corrections": fs.corrections,
                        "is_active": fs.is_active,
                    }
                    for fs in field_specs
                ],
                "prompt_info": {
                    "template_base": fg.prompt_template_base,
                },
            })

        # 第二步：一次性生成统一的 Function Calling Schema
        unified_function_schema = None
        if all_db_fields:
            unified_function_schema = FCSchemaBuilder.build_fc_tools(
                all_db_fields,
                function_name="fill_form",
                include_reason=include_reason,
                description="从对话中提取表单数据"
            )

        # 构建统一字段列表
        all_field_specs = [
            {
                "id": fs.id,
                "field_name": fs.field_name,
                "field_label": fs.field_label,
                "field_type": fs.field_type.value if hasattr(fs.field_type, 'value') else str(fs.field_type),
                "fill_instruction": fs.fill_instruction,
                "options": fs.options,
                "corrections": fs.corrections,
                "is_active": fs.is_active,
            }
            for fs in all_field_specs_map.values()
        ]

        combined_prompt = system_prompts[0] if system_prompts else ""

        return {
            "page_name": page.page_name if page else page_name,
            "field_groups": field_groups_result,
            "all_field_specs": all_field_specs,
            "unified_function_schema": unified_function_schema,
            "combined_prompt": combined_prompt,
        }


field_group_query_service = FieldGroupQueryService()
