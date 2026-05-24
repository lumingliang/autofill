"""
LLM Handler 业务服务层
将 llm_handlers.py 中的业务逻辑下沉到这里
"""
from typing import Any, Dict, Optional

from app.log import logger


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


llm_fill_data_service = LLMFillDataService()
