"""
填单记录管理接口

参考 depts.py 简洁风格：
- 直接在路由函数中调用 Service 层
- 不使用 API 类包装
- 认证由中间件统一处理
"""
from fastapi import APIRouter, Query

from app.schemas.autofill import FillDataRecordUpdate
from app.schemas.base import Fail, Success, SuccessExtra
from app.services.autofill.fill_data_record_service import fill_data_record_service

router = APIRouter()


@router.get("/record/list", summary="填单记录列表")
async def list_record(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    session_id: str = Query("", description="会话ID"),
    phone: str = Query("", description="手机号"),
    user_unique_id: str = Query("", description="用户唯一标识"),
    app_name: str = Query("", description="应用名称"),
):
    """获取填单记录列表"""
    total, records = await fill_data_record_service.list_records(
        session_id=session_id,
        phone=phone,
        user_unique_id=user_unique_id,
        app_name=app_name,
        page=page,
        page_size=page_size
    )
    data = [await obj.to_dict() for obj in records]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/record/get", summary="填单记录详情")
async def get_record(
    id: int = Query(..., description="记录ID"),
):
    """获取填单记录详情"""
    record = await fill_data_record_service.get_record_by_id(record_id=id)
    if not record:
        return Fail(code=404, msg="记录不存在")
    return Success(data=await record.to_dict())


@router.post("/record/update", summary="更新填单记录")
async def update_record(
    record_in: FillDataRecordUpdate,
):
    """更新填单记录"""
    try:
        updated = await fill_data_record_service.update_record(
            record_id=record_in.id,
            record_in=record_in
        )
        return Success(data=await updated.to_dict())
    except ValueError as e:
        return Fail(code=404, msg=str(e))
    except Exception as e:
        return Fail(code=400, msg=f"更新失败: {str(e)}")


@router.delete("/record/delete", summary="删除填单记录")
async def delete_record(
    id: int = Query(..., description="记录ID"),
):
    """删除填单记录"""
    try:
        await fill_data_record_service.delete_record(record_id=id)
        return Success(msg="删除成功")
    except ValueError as e:
        return Fail(code=404, msg=str(e))
    except Exception as e:
        return Fail(code=400, msg=f"删除失败: {str(e)}")
