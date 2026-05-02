"""
比亚迪经销商门店服务
"""
import re
import time
from typing import List, Optional, Dict, Any, Tuple
from tortoise.expressions import Q

from app.models.byd_dealer import BYDDealer, BYDDealerSearchLog
from app.models.autofill import AppManagement
from app.schemas.byd_dealer import (
    BYDDealerCreate,
    BYDDealerUpdate,
    BYDDealerSearchParams,
    BYDDealerPublicSearchRequest,
    BYDDealerPublicSearchResponse,
    BYDDealerResponse
)


class BYDDealerService:
    """比亚迪经销商门店服务"""

    @staticmethod
    async def get_app_by_api_key(api_key: str) -> Optional[AppManagement]:
        """根据 API Key 获取应用信息"""
        return await AppManagement.filter(api_key=api_key, is_active=True).first()

    @staticmethod
    async def create_dealer(data: BYDDealerCreate, tenant_id: int = 0, app_id: int = 0) -> BYDDealer:
        """创建门店"""
        dealer_data = data.model_dump()
        dealer_data["tenant_id"] = tenant_id
        dealer_data["app_id"] = app_id
        dealer = await BYDDealer.create(**dealer_data)
        return dealer

    @staticmethod
    async def get_dealer_by_id(dealer_id: int) -> Optional[BYDDealer]:
        """根据ID获取门店"""
        return await BYDDealer.filter(id=dealer_id).first()

    @staticmethod
    async def get_dealer_by_code(code: str) -> Optional[BYDDealer]:
        """根据编码获取门店"""
        return await BYDDealer.filter(code=code).first()

    @staticmethod
    async def update_dealer(dealer_id: int, data: BYDDealerUpdate) -> Optional[BYDDealer]:
        """更新门店"""
        dealer = await BYDDealer.filter(id=dealer_id).first()
        if not dealer:
            return None

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if update_data:
            await BYDDealer.filter(id=dealer_id).update(**update_data)
            dealer = await BYDDealer.filter(id=dealer_id).first()

        return dealer

    @staticmethod
    async def delete_dealer(dealer_id: int) -> bool:
        """删除门店"""
        deleted = await BYDDealer.filter(id=dealer_id).delete()
        return deleted > 0

    @staticmethod
    async def list_dealers(
        params: BYDDealerSearchParams,
        tenant_id: int = 0,
        app_id: int = 0
    ) -> tuple[List[BYDDealer], int]:
        """门店列表查询"""
        query = BYDDealer.all()

        # 租户和应用过滤
        if tenant_id:
            query = query.filter(tenant_id=tenant_id)
        if app_id:
            query = query.filter(app_id=app_id)

        # 关键词搜索（名称或地址）
        if params.keyword:
            query = query.filter(
                Q(name__icontains=params.keyword) |
                Q(address__icontains=params.keyword)
            )

        # 城市过滤
        if params.city:
            query = query.filter(city__icontains=params.city)

        # 区县过滤
        if params.district:
            query = query.filter(district__icontains=params.district)

        # 门店类型过滤
        if params.dealer_type:
            query = query.filter(dealer_type=params.dealer_type)

        # 状态过滤
        if params.status:
            query = query.filter(status=params.status)

        # 统计总数
        total = await query.count()

        # 分页
        offset = (params.page - 1) * params.page_size
        dealers = await query.offset(offset).limit(params.page_size).all()

        return dealers, total

    @staticmethod
    async def search_dealers(
        request: BYDDealerPublicSearchRequest
    ) -> BYDDealerPublicSearchResponse:
        """
        公开接口搜索门店
        仅支持简单的 %% 模糊查询
        """
        start_time = time.time()
        query_text = request.query

        try:
            # 验证 AppKey 并获取应用信息
            app = await BYDDealerService.get_app_by_api_key(request.app_key)
            if not app:
                return BYDDealerPublicSearchResponse(
                    success=False,
                    data=[],
                    total=0,
                    query=query_text,
                    matched_keywords=[],
                    message="无效的 AppKey"
                )

            # 构建查询条件
            q_objects = Q(tenant_id=app.tenant_id, app_id=app.id)

            # 使用 %% 进行模糊查询
            if query_text:
                q_objects &= (
                    Q(name__icontains=query_text) |
                    Q(address__icontains=query_text) |
                    Q(district__icontains=query_text)
                )

            # 城市过滤（如果提供）
            if request.city:
                q_objects &= Q(city__icontains=request.city)

            # 执行查询
            dealers = await BYDDealer.filter(q_objects).limit(request.limit).all()

            # 转换为响应格式
            dealer_responses = []
            for dealer in dealers:
                dealer_dict = await dealer.to_dict()
                dealer_responses.append(BYDDealerResponse(**dealer_dict))

            response_time = int((time.time() - start_time) * 1000)

            # 记录搜索日志
            await BYDDealerSearchLog.create(
                query=query_text,
                app_key=request.app_key,
                tenant_id=app.tenant_id,
                search_params={"query": query_text, "city": request.city},
                result_count=len(dealers),
                success=True,
                response_time_ms=response_time
            )

            return BYDDealerPublicSearchResponse(
                success=True,
                data=dealer_responses,
                total=len(dealers),
                query=query_text,
                matched_keywords=[query_text] if query_text else [],
                message=f"找到 {len(dealers)} 家门店"
            )

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)

            # 记录错误日志
            await BYDDealerSearchLog.create(
                query=query_text,
                app_key=request.app_key,
                tenant_id=app.tenant_id if app else 0,
                search_params={},
                result_count=0,
                success=False,
                error_msg=str(e),
                response_time_ms=response_time
            )

            return BYDDealerPublicSearchResponse(
                success=False,
                data=[],
                total=0,
                query=query_text,
                matched_keywords=[],
                message=f"搜索失败: {str(e)}"
            )

    @staticmethod
    async def batch_create_dealers(dealers_data: List[Dict[str, Any]], tenant_id: int = 0, app_id: int = 0) -> int:
        """批量创建门店"""
        count = 0
        for data in dealers_data:
            try:
                # 检查是否已存在
                existing = await BYDDealer.filter(code=data.get("code")).first()
                if existing:
                    continue

                data["tenant_id"] = tenant_id
                data["app_id"] = app_id
                await BYDDealer.create(**data)
                count += 1
            except Exception:
                continue

        return count

    @staticmethod
    async def get_all_cities(tenant_id: int = 0, app_id: int = 0) -> List[str]:
        """获取所有城市列表"""
        query = BYDDealer.all()
        if tenant_id:
            query = query.filter(tenant_id=tenant_id)
        if app_id:
            query = query.filter(app_id=app_id)

        dealers = await query.distinct().values("city")
        return sorted([d["city"] for d in dealers if d["city"]])

    @staticmethod
    async def get_statistics(tenant_id: int = 0, app_id: int = 0) -> Dict[str, Any]:
        """获取统计信息"""
        query = BYDDealer.all()
        if tenant_id:
            query = query.filter(tenant_id=tenant_id)
        if app_id:
            query = query.filter(app_id=app_id)

        total = await query.count()
        active = await query.filter(status="营业中").count()

        # 按城市统计
        city_stats = await query.group_by("city").count()

        return {
            "total": total,
            "active": active,
            "city_count": len(city_stats) if isinstance(city_stats, list) else 0
        }
