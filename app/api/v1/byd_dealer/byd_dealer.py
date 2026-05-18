"""
比亚迪经销商门店内部 API (JWT 认证)

本模块提供比亚迪经销商门店的内部管理接口，使用 JWT 认证，
主要供管理后台使用，包含完整的 CRUD 操作。
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from app.core.dependency import get_current_user
from app.schemas.byd_dealer import (
    BYDDealerCreate,
    BYDDealerUpdate,
    BYDDealerResponse,
    BYDDealerSearchParams,
    BYDDealerSearchResponse,
)
from app.services.dealer.byd_dealer_service import BYDDealerService

byd_dealer_router = APIRouter()


@byd_dealer_router.post("/dealers", response_model=BYDDealerResponse, summary="创建门店")
async def create_dealer(
    data: BYDDealerCreate,
    current_user: dict = Depends(get_current_user)
):
    """创建比亚迪经销商门店"""
    # 从当前用户获取租户ID
    tenant_id = current_user.get("tenant_id", 0)
    app_id = current_user.get("app_id", 0)

    dealer = await BYDDealerService.create_dealer(data, tenant_id=tenant_id, app_id=app_id)
    dealer_dict = await dealer.to_dict()
    return BYDDealerResponse(**dealer_dict)


@byd_dealer_router.get("/dealers", response_model=BYDDealerSearchResponse, summary="门店列表")
async def list_dealers(
    keyword: Optional[str] = Query(None, description="关键词"),
    city: Optional[str] = Query(None, description="城市"),
    district: Optional[str] = Query(None, description="区县"),
    dealer_type: Optional[str] = Query(None, description="门店类型"),
    status: Optional[str] = Query(None, description="经营状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(get_current_user)
):
    """获取门店列表（支持分页和过滤）"""
    params = BYDDealerSearchParams(
        keyword=keyword,
        city=city,
        district=district,
        dealer_type=dealer_type,
        status=status,
        page=page,
        page_size=page_size
    )

    tenant_id = current_user.get("tenant_id", 0)
    app_id = current_user.get("app_id", 0)

    dealers, total = await BYDDealerService.list_dealers(params, tenant_id=tenant_id, app_id=app_id)

    dealer_responses = []
    for dealer in dealers:
        dealer_dict = await dealer.to_dict()
        dealer_responses.append(BYDDealerResponse(**dealer_dict))

    return BYDDealerSearchResponse(
        total=total,
        items=dealer_responses,
        page=page,
        page_size=page_size
    )


@byd_dealer_router.get("/dealers/{dealer_id}", response_model=BYDDealerResponse, summary="获取门店详情")
async def get_dealer(
    dealer_id: int,
    current_user: dict = Depends(get_current_user)
):
    """根据ID获取门店详情"""
    dealer = await BYDDealerService.get_dealer_by_id(dealer_id)
    if not dealer:
        raise HTTPException(status_code=404, detail="门店不存在")

    dealer_dict = await dealer.to_dict()
    return BYDDealerResponse(**dealer_dict)


@byd_dealer_router.put("/dealers/{dealer_id}", response_model=BYDDealerResponse, summary="更新门店")
async def update_dealer(
    dealer_id: int,
    data: BYDDealerUpdate,
    current_user: dict = Depends(get_current_user)
):
    """更新门店信息"""
    dealer = await BYDDealerService.update_dealer(dealer_id, data)
    if not dealer:
        raise HTTPException(status_code=404, detail="门店不存在")

    dealer_dict = await dealer.to_dict()
    return BYDDealerResponse(**dealer_dict)


@byd_dealer_router.delete("/dealers/{dealer_id}", summary="删除门店")
async def delete_dealer(
    dealer_id: int,
    current_user: dict = Depends(get_current_user)
):
    """删除门店"""
    success = await BYDDealerService.delete_dealer(dealer_id)
    if not success:
        raise HTTPException(status_code=404, detail="门店不存在")

    return {"success": True, "message": "删除成功"}


@byd_dealer_router.get("/dealers/cities/all", response_model=List[str], summary="获取所有城市")
async def get_all_cities(
    current_user: dict = Depends(get_current_user)
):
    """获取所有有门店的城市列表"""
    tenant_id = current_user.get("tenant_id", 0)
    app_id = current_user.get("app_id", 0)

    cities = await BYDDealerService.get_all_cities(tenant_id=tenant_id, app_id=app_id)
    return cities
