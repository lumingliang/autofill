"""
填单数据相关接口
全部采用POST路由，请求参数使用schema定义
"""
from fastapi import APIRouter, Depends

from app.core.autofill_auth import APIKeyAuth
from app.schemas.base import Success
from app.schemas.public import RecordFillDataRequest
from app.services.autofill.fill_data_record_service import fill_data_record_service

router = APIRouter(tags=["public"])


@router.post("/autofill/record_fill_data", summary="记录填单数据")
async def record_fill_data(
    request: RecordFillDataRequest,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    Dify调用: 记录填单数据，支持数据合并
    只支持 POST 方法
    支持参数传递方式: JSON Body
    """
    app_name = auth_info["app_name"]

    record = await fill_data_record_service.record_fill_data(
        session_id=request.session_id,
        app_name=app_name,
        data=request.data,
        phone=request.phone,
        user_unique_id=request.user_unique_id,
        user_name=request.user_name
    )

    return Success(msg="success", data={"id": record.id})
