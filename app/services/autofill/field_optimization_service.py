"""
字段优化服务
"""
import json
from typing import Any, Dict, List
from fastapi.exceptions import HTTPException
from tortoise.expressions import Q

from app.controllers.autofill import (
    field_group_config_controller,
    field_spec_controller,
)
from app.controllers.llm_config import llm_config_controller
from app.log import logger
from app.models.autofill import FieldGroupFieldSpec
from app.services.llm.structured_output import StructuredOutputService


class FieldOptimizationService:
    """字段优化服务"""
    
    @staticmethod
    async def optimize_field_instructions(
        tenant_id: int,
        app_name: str,
        page_name: str,
        group_name: str = None,
        field_name: str = None,
        batch_size: int = 10,
        model: str = None
    ) -> Dict[str, Any]:
        """优化字段填写指引"""
        page = await field_group_config_controller.model.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            page_name=page_name
        ).first()
        
        if not page:
            raise HTTPException(status_code=404, detail=f"Page '{page_name}' not found")
        
        field_q = Q(tenant_id=tenant_id, app_name=app_name, is_active=True)
        
        if field_name:
            field_q &= Q(field_name=field_name)
        else:
            if group_name:
                field_group = await field_group_config_controller.model.filter(
                    tenant_id=tenant_id,
                    app_name=app_name,
                    page_id=page.id,
                    group_name=group_name
                ).first()
                
                if not field_group:
                    raise HTTPException(status_code=404, detail=f"Field group '{group_name}' not found")
                
                relations = await FieldGroupFieldSpec.filter(
                    field_group_id=field_group.id,
                    tenant_id=tenant_id,
                    app_name=app_name
                ).all()
                field_spec_ids = [r.field_spec_id for r in relations]
                
                if not field_spec_ids:
                    return {"optimized_count": 0, "results": []}
                
                field_q &= Q(id__in=field_spec_ids)
            else:
                field_groups = await field_group_config_controller.model.filter(
                    tenant_id=tenant_id,
                    app_name=app_name,
                    page_id=page.id
                ).all()
                
                if not field_groups:
                    return {"optimized_count": 0, "results": []}
                
                field_group_ids = [fg.id for fg in field_groups]
                relations = await FieldGroupFieldSpec.filter(
                    field_group_id__in=field_group_ids,
                    tenant_id=tenant_id,
                    app_name=app_name
                ).all()
                field_spec_ids = list(set([r.field_spec_id for r in relations]))
                
                if not field_spec_ids:
                    return {"optimized_count": 0, "results": []}
                
                field_q &= Q(id__in=field_spec_ids)
        
        field_specs = await field_spec_controller.model.filter(field_q).all()
        
        if not field_specs:
            return {"optimized_count": 0, "results": []}
        
        config = await llm_config_controller.get_default_config(
            tenant_id=tenant_id,
            app_name=app_name
        )
        
        if not config:
            raise HTTPException(status_code=500, detail="No LLM configuration found")
        
        if model:
            config.model = model
        
        results = []
        total_count = len(field_specs)
        
        for i in range(0, total_count, batch_size):
            batch = field_specs[i:i + batch_size]
            batch_results = await FieldOptimizationService._optimize_batch(
                fields=batch,
                config=config
            )
            results.extend(batch_results)
        
        return {
            "optimized_count": len([r for r in results if r["success"]]),
            "total_count": total_count,
            "results": results
        }
    
    @staticmethod
    async def _optimize_batch(fields: List, config) -> List[Dict[str, Any]]:
        """优化一批字段"""
        results = []
        
        if not fields:
            return results
        
        service = StructuredOutputService(config)
        
        fields_info = []
        for field in fields:
            field_type = field.field_type.value if field.field_type else "text"
            field_info = {
                "field_name": field.field_name,
                "field_label": field.field_label or field.field_name,
                "field_type": field_type,
                "current_instruction": field.fill_instruction or "",
                "options": field.options.get("items", []) if field.options and field_type in ["select_single", "select_multi"] else []
            }
            fields_info.append(field_info)
        
        field_names_list = [f["field_name"] for f in fields_info]
        fields_text = json.dumps(fields_info, ensure_ascii=False, indent=2)
        
        properties = {}
        for field_info in fields_info:
            field_name = field_info["field_name"]
            properties[field_name] = {
                "type": "string",
                "description": f"优化后的填写指引（原指引：{field_info['current_instruction'][:50] if field_info['current_instruction'] else '无'}...）"
            }
        
        function_schema = {
            "type": "function",
            "function": {
                "name": "optimize_field_instructions",
                "description": f"优化以下字段的填写指引：{', '.join(field_names_list)}",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": list(properties.keys())
                }
            }
        }
        
        prompt = f"""你是一个专业的表单设计专家。请优化以下字段的填写指引。

需要优化的字段列表：
{fields_text}

优化要求：
1. 清晰描述每个字段的用途和填写要求
2. 对于下拉选择字段，说明如何选择合适的选项，包含常见场景的判断逻辑
3. 对于文本字段，说明应该提取什么样的信息，包含常见格式的示例
4. 使用简洁专业的语言
5. 保持原有指引的核心信息，但使其更加清晰和易于理解
6. **重要**：optimize_field_instructions 函数的每个参数名对应一个字段名，参数值为该字段优化后的填写指引

请调用 optimize_field_instructions 函数，为每个字段返回优化后的填写指引。"""
        
        try:
            result = await service.generate(
                query=prompt,
                tools=[function_schema],
                system_prompt="你是一个专业的表单设计专家，擅长编写清晰、准确的字段填写指引。",
                tool_choice={"type": "function", "function": {"name": "optimize_field_instructions"}},
                method="bind_tools_non_stream"
            )
            
            if not result.success:
                raise ValueError(f"Failed to generate: {result.error}")
            
            optimized_map = result.data
            
            for field in fields:
                field_label = field.field_label or field.field_name
                current_instruction = field.fill_instruction or ""
                
                if field.field_name in optimized_map:
                    optimized_instruction = optimized_map[field.field_name].strip()
                    
                    if optimized_instruction:
                        await field_spec_controller.update(
                            id=field.id,
                            obj_in={"fill_instruction": optimized_instruction}
                        )
                        
                        results.append({
                            "field_name": field.field_name,
                            "field_label": field_label,
                            "success": True,
                            "original_instruction": current_instruction,
                            "optimized_instruction": optimized_instruction
                        })
                    else:
                        results.append({
                            "field_name": field.field_name,
                            "field_label": field_label,
                            "success": False,
                            "error": "LLM returned empty instruction"
                        })
                else:
                    results.append({
                        "field_name": field.field_name,
                        "field_label": field_label,
                        "success": False,
                        "error": f"Field not found in LLM response. Available: {list(optimized_map.keys())}"
                    })
        
        except Exception as e:
            logger.error(f"Failed to optimize batch: {e}")
            for field in fields:
                results.append({
                    "field_name": field.field_name,
                    "field_label": field.field_label or field.field_name,
                    "success": False,
                    "error": str(e)
                })
        
        return results


field_optimization_service = FieldOptimizationService()
