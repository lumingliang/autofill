"""
反馈内容总结接口
"""
import uuid

from fastapi import APIRouter, Request

from app.core.ctx import Ctx
from app.log import logger
from app.schemas.base import Success
from app.schemas.open import SummaryFeedbackRequest
from app.services.autofill.rule_engine_service import rule_engine_service

router = APIRouter()


def _extract_summary_from_rule_result(result: dict) -> str:
    """从规则引擎结果中提取总结内容

    规则引擎返回结构: {"results": {"feedback_summary_35": {"llm_res": "总结内容", ...}}}
    """
    if not result:
        return ""

    results = result.get("results", {})
    rule_result = results.get("feedback_summary_35", {})

    llm_res = rule_result.get("llm_res", "")
    return str(llm_res).strip() if llm_res else ""


@router.post("/autofill/summary-feedback", summary="反馈内容总结")
async def summary_feedback(
    request: SummaryFeedbackRequest,
    http_request: Request,
):
    """
    反馈内容总结接口

    - **order_id**: 工单ID（唯一标识）
    - **brand**: 品牌
    - **feedback_content**: 反馈内容（需要总结的文本）
    - **callback**: 回调信息

    注意：租户ID通过 Ctx 自动获取，无需手动传递
    """
    # 从中间件设置的 state 中获取认证信息
    auth_info = getattr(http_request.state, "auth_info", {})
    app_name = auth_info.get("app_name", "")

    random_num = uuid.uuid4().hex[:8]
    session_id = f"{request.order_id}_{random_num}"

    logger.info(f"[SummaryFeedback] order_id={request.order_id}, brand={request.brand}, app_name={app_name}")

    try:
        result = await rule_engine_service.summary_feedback(
            session_id=session_id,
            order_id=request.order_id,
            brand=request.brand,
            feedback_content=request.feedback_content,
            callback=request.callback,
            app_name=app_name,
        )

        summary = _extract_summary_from_rule_result(result)

        return Success(data={
            "order_id": request.order_id,
            "summary": summary,
            "session_id": session_id,
        })

    except Exception as e:
        logger.error(f"[SummaryFeedback] Error: {e}")
        return Success(data={
            "order_id": request.order_id,
            "summary": "",
            "session_id": session_id,
        })
