"""
字段明细相关接口（优化版本）
全部采用POST路由，请求参数使用schema定义
"""
from fastapi import APIRouter, Depends, Request

from app.core.autofill_auth import APIKeyAuth
from app.core.request_parser import parse_request_params
from app.schemas.base import Success
from app.schemas.public import UpsertFieldGroupRequest
from app.services.autofill.field_group_service import field_group_service

router = APIRouter(tags=["public"])


@router.post("/autofill/field_group/upsert", summary="创建或更新字段组（含批量字段）")
async def upsert_field_group(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    创建或更新字段组，并批量处理字段列表
    """
    params = await parse_request_params(request, UpsertFieldGroupRequest)
    
    result = await field_group_service.upsert_field_group(
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"],
        group_name=params["group_name"],
        group_code=params.get("group_code"),
        output_templates=params.get("output_templates"),
        prompt_template_base=params.get("prompt_template_base"),
        fields=params.get("fields")
    )
    
    return Success(data=result)
