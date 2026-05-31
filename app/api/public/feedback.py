"""
反馈内容总结接口
"""
import uuid

from fastapi import APIRouter, Depends

from app.core.autofill_auth import APIKeyAuth
from app.log import logger
from app.schemas.base import Success
from app.schemas.public import SummaryFeedbackRequest
from app.services.autofill.rule_engine_service import rule_engine_service

router = APIRouter(tags=["public"])


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
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    反馈内容总结接口

    - **order_id**: 工单ID（唯一标识）
    - **brand**: 品牌
    - **feedback_content**: 反馈内容（需要总结的文本）
    - **callback**: 回调信息

    注意：租户ID通过 Ctx 自动获取，无需手动传递
    """
    app_name = auth_info["app_name"]

    random_num = uuid.uuid4().hex[:8]
    session_id = f"{request.order_id}_{random_num}"

    logger.info(f"Summary feedback: order_id={request.order_id}, session_id={session_id}, brand={request.brand}")

    try:
        result = await rule_engine_service.execute_rule(
            app_name=app_name,
            session_id=session_id,
            query=request.feedback_content,
            method="plain",
            temperature=0.7,
            params=[
                {
                    "rule_name": "feedback_summary_35",
                    "prompt": {
                        "type": "text",
                        "select_fields": ["规则"],
                        "name_fields": ["场景"],
                        "rule_fields": ["规则"],
                        "filter": {"场景": "通用场景"}
                    }
                }
            ],
            step=1,
            is_last=True,
            system_prompt_name="35字总结提示词"
        )

        summary = _extract_summary_from_rule_result(result)

        logger.info(f"Summary feedback result: order_id={request.order_id}, summary={summary}")

        return Success(data={
            "order_id": request.order_id,
            "summary": summary
        })

    except ValueError as e:
        logger.error(f"Summary feedback validation error: {e}")
        return Success(code=400, message=str(e), data={"order_id": request.order_id, "summary": ""})

    except Exception as e:
        logger.error(f"Summary feedback error: {e}")
        return Success(code=500, message=f"处理失败: {str(e)}", data={"order_id": request.order_id, "summary": ""})
