"""
反馈内容总结接口
"""
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.autofill_auth import APIKeyAuth
from app.log import logger
from app.schemas.base import Success
from app.services.autofill.rule_engine_service import rule_engine_service

router = APIRouter(tags=["public"])


class SummaryFeedbackRequest(BaseModel):
    """反馈内容总结请求"""
    order_id: str = Field(..., description="工单ID（唯一标识）")
    brand: str = Field(..., description="品牌")
    feedback_content: str = Field(..., description="反馈内容（需要总结的文本）")
    callback: str = Field(default="", description="回调信息")


def _extract_summary_from_rule_result(result: dict) -> str:
    """从规则引擎结果中提取总结内容
    
    规则引擎返回结构: {"results": {"feedback_summary_35": {"llm_res": "总结内容", ...}}}
    """
    if not result:
        return ""
    
    results = result.get("results", {})
    rule_result = results.get("feedback_summary_35", {})
    
    # 获取 llm_res 字段
    llm_res = rule_result.get("llm_res", "")
    # 只去除前后空格，不做其他处理（提示词已优化）
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
    """
    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 1. 生成 session_id
    random_num = uuid.uuid4().hex[:8]
    session_id = f"{request.order_id}_{random_num}"

    logger.info(f"Summary feedback: order_id={request.order_id}, session_id={session_id}, brand={request.brand}")

    try:
        # 使用规则引擎执行
        result = await rule_engine_service.execute_rule(
            tenant_id=tenant_id,
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
        
        # 从规则引擎结果中提取总结
        summary = _extract_summary_from_rule_result(result)

        logger.info(f"Summary feedback result: order_id={request.order_id}, summary={summary}")

        # 返回响应
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
