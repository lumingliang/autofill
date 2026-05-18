"""
字段查询服务
"""
from typing import Any, Dict, List, Optional

from fastapi.exceptions import HTTPException
from tortoise.expressions import Q

from app.controllers.autofill import (
    field_group_config_controller,
    field_spec_controller,
    fill_page_controller,
)
from app.models.autofill import FieldGroupFieldSpec


class FieldSpecService:
    """字段规格服务"""
    
    @staticmethod
    async def create_field_spec(
        tenant_id: int,
        app_name: str,
        field_group_id: int,
        field_name: str,
        field_label: str,
        field_type: str = "text",
        fill_instruction: str = "",
        options: Optional[Dict] = None,
        corrections: Optional[List] = None,
        is_active: bool = True
    ) -> Dict[str, Any]:
        """公共接口：创建字段明细"""
        
        # 1. 验证字段组存在
        field_group = await field_group_config_controller.model.filter(
            id=field_group_id,
            tenant_id=tenant_id,
            app_name=app_name
        ).first()
        
        if not field_group:
            raise HTTPException(status_code=404, detail="Field group not found")
        
        # 2. 检查字段是否已存在
        existing = await field_spec_controller.model.filter(
            field_group_id=field_group_id,
            field_name=field_name
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Field name already exists in this group")
        
        # 3. 创建字段
        field_data = {
            "field_group_id": field_group_id,
            "field_name": field_name,
            "field_label": field_label,
            "field_type": field_type,
            "fill_instruction": fill_instruction,
            "options": options or {},
            "corrections": corrections or [],
            "is_active": is_active,
            "tenant_id": tenant_id,
            "app_name": app_name,
        }
        
        spec = await field_spec_controller.create(obj_in=field_data)
        
        return {
            "id": spec.id,
            "field_name": spec.field_name,
            "field_label": spec.field_label,
            "field_type": spec.field_type,
        }


field_spec_service = FieldSpecService()
