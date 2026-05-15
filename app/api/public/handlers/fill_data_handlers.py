"""
填单数据相关接口
全部采用POST路由，请求参数使用schema定义
"""
from fastapi import APIRouter, Depends, Request

from app.controllers.autofill import fill_data_record_controller
from app.core.autofill_auth import APIKeyAuth
from app.core.request_parser import parse_request_params
from app.schemas.base import Success
from app.schemas.public import RecordFillDataRequest

router = APIRouter()


async def record_fill_data_handler(request: Request, auth_info: dict):
    """记录填单数据处理逻辑"""
    params = await parse_request_params(request, RecordFillDataRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    record = await fill_data_record_controller.record_fill_data(
        session_id=params["session_id"],
        tenant_id=tenant_id,
        app_name=app_name,
        data=params.get("data", {}),
        phone=params.get("phone"),
        user_unique_id=params.get("user_unique_id"),
        user_name=params.get("user_name")
    )

    return Success(msg="success", data={"id": record.id})


@router.post("/autofill/record_fill_data", summary="记录填单数据")
async def record_fill_data(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    Dify调用: 记录填单数据，支持数据合并
    只支持 POST 方法
    支持参数传递方式: JSON Body
    """
    return await record_fill_data_handler(request, auth_info)
