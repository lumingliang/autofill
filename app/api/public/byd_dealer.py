"""
比亚迪经销商门店公开 API (API Key 认证)

本模块提供比亚迪经销商门店的公开查询接口，使用 API Key 认证，
主要供 Dify、三方应用和外部系统调用。
"""
from fastapi import APIRouter, Depends

from app.core.autofill_auth import APIKeyAuth
from app.schemas.byd_dealer import (
    BYDDealerPublicSearchRequest,
    BYDDealerPublicSearchResponse,
)
from app.services.byd_dealer_service import BYDDealerService

byd_dealer_public_router = APIRouter()


@byd_dealer_public_router.post(
    "/byd-dealers/search",
    response_model=BYDDealerPublicSearchResponse,
    summary="公开搜索门店"
)
async def public_search_dealers(
    request: BYDDealerPublicSearchRequest,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    公开搜索接口（基于 AppKey 认证）

    支持通过门店名称、地址、城市进行模糊查询
    """
    return await BYDDealerService.search_dealers(request)
