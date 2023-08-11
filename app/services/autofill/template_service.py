"""
模板相关服务
"""
from typing import Any, Dict, List, Optional

from fastapi.exceptions import HTTPException
from tortoise.expressions import Q

from app.controllers.autofill import summary_template_controller


class TemplateService:
    """模板服务"""
    
    @staticmethod
    async def list_summary_templates(
        tenant_id: int,
        app_name: str,
        class_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """查询模板列表"""
        
        q = summary_template_controller.model.filter(
            tenant_id=tenant_id,
            app_name=app_name
        )
        
        if class_name:
            q = q.filter(class_name=class_name)
        
        templates = await q.all()
        
        return [
            {
                "id": t.id, 
                "name": t.name, 
                "summary": t.summary, 
                "class_name": t.class_name
            }
            for t in templates
        ]
    
    @staticmethod
    async def get_summary_template(
        tenant_id: int,
        app_name: str,
        template_id: int
    ) -> Dict[str, Any]:
        """查询模板详情"""
        
        template = await summary_template_controller.model.filter(
            id=template_id,
            tenant_id=tenant_id,
            app_name=app_name
        ).first()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {
            "id": template.id,
            "name": template.name,
            "summary": template.summary,
            "class_name": template.class_name,
            "template_content": template.template_content
        }


template_service = TemplateService()
