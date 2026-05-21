"""
字段组查询服务 - 直接关联应用，不再关联页面
"""
from typing import Any, Dict, List, Optional, Tuple

from app.models.autofill import FieldGroupConfig, FieldSpec, FieldGroupFieldSpec
from app.services.llm.structured_output.schema_builder import FCSchemaBuilder


class FieldGroupQueryService:
    """字段组查询服务 - 新实现：直接关联应用"""

    @staticmethod
    async def fetch_field_groups(
        tenant_id: int,
        app_name: str,
        group_names: List[str] = None,
        field_names: List[str] = None,
        additional_data: Dict[str, Any] = None,
        use_additional_data: bool = False,
        include_reason: bool = False
    ) -> Dict[str, Any]:
        """
        查询字段组配置核心业务逻辑

        设计说明：
        - 字段的唯一索引是 field_name + tenant_id + app_name
        - FieldGroupFieldSpec 仅用于管理字段组和字段的映射关系
        - 查询策略：
          1. 如果指定了 field_names：直接查询这些字段
          2. 如果指定了 group_names：查询这些字段组下的所有字段
          3. 如果都没指定：查询该应用下所有字段组的所有字段
        """
        group_names = group_names or []
        field_names = field_names or []

        # 参数验证
        if not tenant_id or not app_name:
            raise ValueError("tenant_id 和 app_name 不能为空")

        # 1. 查询字段组
        q = FieldGroupConfig.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            is_active=True
        )

        # 如果指定了字段组名称，则过滤
        if group_names:
            q = q.filter(group_name__in=group_names)

        field_groups = await q.all()

        if not field_groups:
            return {
                "app_name": app_name,
                "field_groups": [],
                "all_field_specs": [],
                "unified_function_schema": None,
                "combined_prompt": "",
                "group_template_map": {},
            }

        # 2. 批量查询字段
        all_field_specs_map, group_to_spec_ids = await FieldGroupQueryService._batch_query_fields(
            field_groups,
            field_names,
            tenant_id,
            app_name
        )

        # 3. 组装结果
        return FieldGroupQueryService._assemble_result(
            field_groups,
            all_field_specs_map,
            group_to_spec_ids,
            field_names,
            additional_data,
            use_additional_data,
            include_reason,
            app_name
        )

    @staticmethod
    async def _batch_query_fields(
        field_groups: List,
        field_names: List[str],
        tenant_id: int,
        app_name: str
    ) -> Tuple[Dict, Dict]:
        """批量查询字段策略 - 简化版
        
        1. 根据 field_names 查询指定字段
        2. 根据 field_groups 查询每个组下的所有字段
        3. 合并结果
        """
        all_field_specs_map = {}
        group_to_spec_ids = {}
        
        # 1. 根据 field_names 查询指定字段
        if field_names:
            specified_fields = await FieldSpec.filter(
                tenant_id=tenant_id,
                app_name=app_name,
                field_name__in=field_names,
                is_active=True
            ).all()
            for fs in specified_fields:
                all_field_specs_map[fs.field_name] = fs
        
        # 2. 根据 field_groups 查询每个组下的所有字段
        if field_groups:
            group_ids = [fg.id for fg in field_groups]
            relations = await FieldGroupFieldSpec.filter(
                field_group_id__in=group_ids,
                tenant_id=tenant_id,
                app_name=app_name
            ).all()
            
            for r in relations:
                if r.field_group_id not in group_to_spec_ids:
                    group_to_spec_ids[r.field_group_id] = []
                group_to_spec_ids[r.field_group_id].append(r.field_spec_id)
            
            all_spec_ids = [sid for ids in group_to_spec_ids.values() for sid in ids]
            if all_spec_ids:
                group_fields = await FieldSpec.filter(
                    id__in=all_spec_ids,
                    tenant_id=tenant_id,
                    app_name=app_name,
                    is_active=True
                ).all()
                for fs in group_fields:
                    all_field_specs_map[fs.field_name] = fs
        
        return all_field_specs_map, group_to_spec_ids

    @staticmethod
    def _assemble_result(
        field_groups: List,
        all_field_specs_map: Dict,
        group_to_spec_ids: Dict,
        field_names: List[str],
        additional_data: Dict[str, Any],
        use_additional_data: bool,
        include_reason: bool,
        app_name: str
    ) -> Dict[str, Any]:
        """组装结果返回 - 简化版
        
        直接使用 all_field_specs_map 中的字段，不需要再通过 group_to_spec_ids 筛选
        """
        # 获取所有字段
        all_field_specs_list = list(all_field_specs_map.values())
        
        # 如果指定了 field_names，过滤字段
        if field_names:
            all_field_specs_list = [fs for fs in all_field_specs_list if fs.field_name in field_names]
        
        # 使用附加数据过滤
        additional_field_names = set(additional_data.keys()) if use_additional_data and additional_data else set()
        if use_additional_data and additional_field_names:
            all_field_specs_list = [fs for fs in all_field_specs_list if fs.field_name not in additional_field_names]
        
        # 构建字段组模板映射
        group_template_map = {fg.group_name: fg.prompt_template_base for fg in field_groups}
        
        # 收集系统提示词（取第一个字段组的模板）
        system_prompt = ""
        for fg in field_groups:
            if fg.prompt_template_base:
                system_prompt = fg.prompt_template_base
                break
        
        # 构建 db_fields 用于生成 schema
        db_fields = [
            {
                "field_name": fs.field_name,
                "field_label": fs.field_label,
                "field_type": fs.field_type.value if hasattr(fs.field_type, 'value') else fs.field_type,
                "fill_instruction": fs.fill_instruction,
                "options": fs.options,
                "corrections": fs.corrections,
            }
            for fs in all_field_specs_list
        ]
        
        # 生成统一的 Function Calling Schema
        unified_function_schema = None
        if db_fields:
            unified_function_schema = FCSchemaBuilder.build_fc_tools(
                db_fields,
                function_name="fill_form",
                include_reason=include_reason,
                description="从对话中提取表单数据"
            )
        
        # 构建返回的字段列表
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
            for fs in all_field_specs_list
        ]
        
        # 构建字段组结果（简化版，只包含基本信息）
        field_groups_result = [
            {
                "id": fg.id,
                "group_name": fg.group_name,
                "group_code": fg.group_code,
                "app_name": fg.app_name,
                "prompt_template_base": fg.prompt_template_base,
                "output_templates": fg.output_templates or {},
                "version": fg.version,
                "is_active": fg.is_active,
                "description": fg.description,
            }
            for fg in field_groups
        ]
        
        return {
            "app_name": app_name,
            "field_groups": field_groups_result,
            "all_field_specs": all_field_specs,
            "unified_function_schema": unified_function_schema,
            "combined_prompt": system_prompt,
            "group_template_map": group_template_map,
        }


field_group_query_service = FieldGroupQueryService()
