"""
字段组相关接口（优化版本）
全部采用POST路由，请求参数使用schema定义
"""
from fastapi import APIRouter, Depends, Request

from app.core.autofill_auth import APIKeyAuth
from app.core.request_parser import parse_request_params
from app.schemas.base import Success
from app.schemas.public import FieldGroupRequest
from app.services.autofill.field_group_query_service import field_group_query_service

router = APIRouter()


@router.post("/autofill/field_group", summary="查询字段组配置")
async def get_field_group(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    根据app_name/page_name/字段组名或code查询字段组配置
    """
    params = await parse_request_params(request, FieldGroupRequest)
    
    result = await field_group_query_service.fetch_field_groups(
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"],
        page_name=params.get("page_name"),
        group_fields=params.get("group_fields", {})
    )
    
    return Success(data=result.get("field_groups", []))
