"""
填单数据相关接口
全部采用POST路由，请求参数使用schema定义
"""
from fastapi import APIRouter, Request

from app.schemas.base import Success
from app.schemas.open import RecordFillDataRequest
from app.services.autofill.fill_data_record_service import fill_data_record_service

router = APIRouter()


@router.post("/autofill/record_fill_data", summary="记录填单数据")
async def record_fill_data(
    request: RecordFillDataRequest,
    http_request: Request,
):
    """
    Dify调用: 记录填单数据，支持数据合并
    只支持 POST 方法
    支持参数传递方式: JSON Body
    """
    # 从中间件设置的 state 中获取认证信息
    auth_info = getattr(http_request.state, "auth_info", {})
    app_name = auth_info.get("app_name", "")

    record = await fill_data_record_service.record_fill_data(
        session_id=request.session_id,
        app_name=app_name,
        data=request.data,
        phone=request.phone,
        user_unique_id=request.user_unique_id,
        user_name=request.user_name
    )

    return Success(msg="success", data={"id": record.id})
