"""
反馈内容总结接口
"""
import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.autofill_auth import APIKeyAuth
from app.log import logger
from app.schemas.base import Success
from app.services.autofill.step_llm_fill_service import step_llm_fill_service

router = APIRouter(tags=["public"])


class SummaryFeedbackRequest(BaseModel):
    """反馈内容总结请求"""
    order_id: str = Field(..., description="工单ID（唯一标识）")
    brand: str = Field(..., description="品牌")
    feedback_content: str = Field(..., description="反馈内容（需要总结的文本）")
    callback: str = Field(default="", description="回调信息")


def _extract_field_value(field_data: Any) -> str:
    """从字段数据中提取值"""
    if field_data is None:
        return ""
    if isinstance(field_data, str):
        return field_data
    if isinstance(field_data, dict):
        if "value" in field_data:
            value = field_data["value"]
            if isinstance(value, dict):
                return str(value.get("value", ""))
            if isinstance(value, list):
                return ", ".join([str(v.get("value", v) if isinstance(v, dict) else v) for v in value])
            return str(value)
        return str(field_data)
    return str(field_data)


@router.post("/autofill/summary-feedback", summary="反馈内容总结")
async def summary_feedback(
    request: SummaryFeedbackRequest,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    反馈内容总结接口

    - **order_id**: 工单ID（唯一标识）
    - **brand**: 品牌
    - **feedback_content**: 反馈内容（需要总结的文本）
    - **callback**: 回调信息
    """
    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 1. 生成 session_id
    random_num = uuid.uuid4().hex[:8]
    session_id = f"{request.order_id}_{random_num}"

    logger.info(f"Summary feedback: order_id={request.order_id}, session_id={session_id}, brand={request.brand}")

    try:
        # 2. 调用 service 层执行 LLM 填单
        result = await step_llm_fill_service.execute_llm_fill_step(
            tenant_id=tenant_id,
            app_name=app_name,
            page_name="common",
            session_id=session_id,
            group_fields={"default": ["feedback_content_summary"]},
            query=request.feedback_content,
            is_last=True
        )

        # 3. 解析结果，提取 feedback_content_summary
        summary = ""
        enriched_result = result.get("result", {})

        if "feedback_content_summary" in enriched_result:
            field_data = enriched_result["feedback_content_summary"]
            summary = _extract_field_value(field_data)



        logger.info(f"Summary feedback result: order_id={request.order_id}, summary={summary}")

        # 4. 返回响应
        return Success(data={
            "order_id": request.order_id,
            "summary": summary
        })

    except ValueError as e:
        logger.error(f"Summary feedback validation error: {e}")
        await step_llm_fill_service.save_step_error(
            session_id=session_id,
            tenant_id=tenant_id,
            app_name=app_name,
            error_msg=str(e)
        )
        return Success(code=400, message=str(e), data={"order_id": request.order_id, "summary": ""})

    except Exception as e:
        logger.error(f"Summary feedback error: {e}")
        await step_llm_fill_service.save_step_error(
            session_id=session_id,
            tenant_id=tenant_id,
            app_name=app_name,
            error_msg=str(e)
        )
        return Success(code=500, message=f"处理失败: {str(e)}", data={"order_id": request.order_id, "summary": ""})
