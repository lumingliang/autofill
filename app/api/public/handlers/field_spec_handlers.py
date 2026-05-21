"""
字段明细相关接口（优化版本）
全部采用POST路由，请求参数使用schema定义
"""
from fastapi import APIRouter, Depends, Request

from app.core.autofill_auth import APIKeyAuth
from app.core.request_parser import parse_request_params
from app.schemas.base import Success
from app.schemas.public import (
    FieldSpecListRequest,
    FieldSpecCreateRequest,
    UpsertFieldGroupRequest,
)
from app.services.autofill.field_group_service import field_group_service
from app.services.autofill.field_spec_service_v2 import field_spec_service

router = APIRouter(tags=["public"])


@router.post("/autofill/field_spec/list", summary="查询字段明细列表")
async def list_field_spec(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    根据app_name/group_names查询字段明细列表
    """
    params = await parse_request_params(request, FieldSpecListRequest)
    
    result = await field_group_service.list_field_specs(
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"],
        group_names=params.get("group_names"),
        field_names=params.get("field_names")
    )
    
    return Success(data=result)


@router.post("/autofill/field_spec/create", summary="公共接口：创建字段明细")
async def create_field_spec_public(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """公共接口：创建字段明细"""
    params = await parse_request_params(request, FieldSpecCreateRequest)

    result = await field_spec_service.create_field_spec(
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"],
        field_name=params["field_name"],
        field_label=params["field_label"],
        field_type=params.get("field_type", "text"),
        fill_instruction=params.get("fill_instruction", ""),
        options=params.get("options", {})
    )

    return Success(data=result)


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
