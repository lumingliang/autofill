"""
模板相关接口（优化版本）
全部采用POST路由，请求参数使用schema定义
"""
from fastapi import APIRouter, Depends, Request

from app.core.autofill_auth import APIKeyAuth
from app.core.request_parser import parse_request_params
from app.schemas.base import Success
from app.schemas.public import (
    SummaryTemplateListRequest,
    SummaryTemplateDetailRequest,
)
from app.services.autofill.template_service import template_service

router = APIRouter()


@router.post("/autofill/summary_template/list", summary="查询模板列表")
async def list_summary_templates(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    Dify调用: 根据 tenant_id + app_name + class_name 查询模板列表
    """
    params = await parse_request_params(request, SummaryTemplateListRequest)
    
    result = await template_service.list_summary_templates(
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"],
        class_name=params.get("class_name")
    )
    
    return Success(data=result)


@router.post("/autofill/summary_template", summary="查询模板详情")
async def get_summary_template(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    Dify调用: 根据ID查询模板详情
    """
    params = await parse_request_params(request, SummaryTemplateDetailRequest)
    
    result = await template_service.get_summary_template(
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"],
        template_id=params["id"]
    )
    
    return Success(data=result)
