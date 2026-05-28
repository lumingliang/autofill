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
from app.services.autofill.step_llm_fill_service import step_llm_fill_service
from app.services.autofill.rule_engine_service import rule_engine_service

router = APIRouter(tags=["public"])


class SummaryFeedbackRequest(BaseModel):
    """反馈内容总结请求"""
    order_id: str = Field(..., description="工单ID（唯一标识）")
    brand: str = Field(..., description="品牌")
    feedback_content: str = Field(..., description="反馈内容（需要总结的文本）")
    callback: str = Field(default="", description="回调信息")
    use_rule_engine: bool = Field(default=True, description="是否使用规则引擎执行，默认为True")


def _extract_summary_from_result(result: dict) -> str:
    """从 plain 模式结果中提取总结内容
    
    plain 模式返回结构: {"feedback_content_summary": {"type": "text", "value": "总结内容", "label": "..."}}
    或者直接返回文本在 value 中
    """
    if not result:
        return ""
    
    # 获取 feedback_content_summary 字段
    field_data = result.get("feedback_content_summary")
    if not field_data:
        return ""
    
    # 如果是字符串，直接返回
    if isinstance(field_data, str):
        return field_data
    
    # 如果是字典，提取 value
    if isinstance(field_data, dict):
        value = field_data.get("value", "")
        # 处理嵌套结构（兼容旧格式）
        if isinstance(value, dict):
            return str(value.get("value", ""))
        return str(value)
    
    return str(field_data)


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
    - **use_rule_engine**: 是否使用规则引擎执行，默认为True
    """
    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 1. 生成 session_id
    random_num = uuid.uuid4().hex[:8]
    session_id = f"{request.order_id}_{random_num}"

    logger.info(f"Summary feedback: order_id={request.order_id}, session_id={session_id}, brand={request.brand}, use_rule_engine={request.use_rule_engine}")

    try:
        if request.use_rule_engine:
            # 使用规则引擎执行（默认）
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
        else:
            # 使用原有的 step_llm_fill_service 执行（兼容旧模式）
            result = await step_llm_fill_service.execute_llm_fill_step(
                tenant_id=tenant_id,
                app_name=app_name,
                session_id=session_id,
                group_names=["default"],
                field_names=["feedback_content_summary"],
                system_prompt_group=None,
                query=request.feedback_content,
                is_last=True,
                method="plain",
                system_prompt="你是一个专业的客服反馈总结助手。请对用户的反馈内容进行简洁的总结，提取关键问题和需求。总结应该简明扼要，不超过100字。"
            )
            
            # 从原有结果中提取总结
            summary = _extract_summary_from_result(result.get("result", {}))

        logger.info(f"Summary feedback result: order_id={request.order_id}, summary={summary}")

        # 返回响应
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
