"""
规则执行引擎接口
提供基于CSV规则的选择题和填空题执行能力
"""
from fastapi import APIRouter, Request
from fastapi.exceptions import HTTPException

from app.log import logger
from app.schemas.base import Success
from app.schemas.open import RuleExecuteRequest, RuleExecuteResultRequest
from app.services.autofill.rule_engine_service import rule_engine_service

router = APIRouter()


@router.post("/autofill/llm/rule/execute", summary="规则执行引擎")
async def execute_rule(
    request: RuleExecuteRequest,
    http_request: Request,
):
    """
    执行规则引擎

    支持选择题(choice)和填空题(text)两种任务类型
    支持多任务混合执行
    支持多步填单流程

    请求示例:
    ```json
    {
        "session_id": "sess_001",
        "query": "我买的手机屏幕碎了，我要投诉",
        "method": "plain",
        "temperature": 0.7,
        "step": 1,
        "is_last": true,
        "params": [
            {
                "rule_name": "event_type",
                "prompt": {
                    "type": "choice",
                    "filter": {"一级事件类型": "投诉"},
                    "select_fields": ["二级事件类型id", "三级事件类型id"],
                    "name_fields": ["二级事件类型", "三级事件类型"],
                    "rule_fields": ["二级事件类型填写规则", "三级事件类型填写规则"],
                    "name_separator": " - "
                }
            }
        ]
    }
    ```
    """
    # 从中间件设置的 state 中获取认证信息
    auth_info = getattr(http_request.state, "auth_info", {})
    app_name = auth_info.get("app_name", "")

    # 智能method适配：多任务默认json_parser，单任务默认plain
    method = request.method
    if not method:
        method = "json_parser" if len(request.params) > 1 else "plain"

    logger.info(
        f"Rule execute: session_id={request.session_id}, step={request.step}, "
        f"is_last={request.is_last}, method={method}, params_count={len(request.params)}"
    )

    # 转换params为字典格式供service使用
    params_dict = []
    for param in request.params:
        prompt_config = {
            "type": param.prompt.type,
            "select_fields": param.prompt.select_fields,
            "name_fields": param.prompt.name_fields,
            "rule_fields": param.prompt.rule_fields,
        }
        if param.prompt.filter is not None:
            prompt_config["filter"] = param.prompt.filter
        if param.prompt.name_separator is not None:
            prompt_config["name_separator"] = param.prompt.name_separator
        if param.prompt.system_prompt_name is not None:
            prompt_config["system_prompt_name"] = param.prompt.system_prompt_name

        params_dict.append({
            "rule_name": param.rule_name,
            "prompt": prompt_config
        })

    try:
        result = await rule_engine_service.execute_rule(
            app_name=app_name,
            session_id=request.session_id,
            query=request.query,
            method=method,
            temperature=request.temperature,
            params=params_dict,
            step=request.step,
            is_last=request.is_last,
            system_prompt=request.system_prompt,
            system_prompt_name=request.system_prompt_name
        )

        return Success(data=result)

    except ValueError as e:
        logger.error(f"Rule execute validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Rule execute error: {e}")
        raise HTTPException(status_code=500, detail=f"Rule execution failed: {str(e)}")


@router.post("/autofill/llm/rule/execute/result", summary="获取规则执行结果")
async def get_rule_execute_result(
    request: RuleExecuteResultRequest,
    http_request: Request,
):
    """
    获取规则执行的完整结果

    请求示例:
    ```json
    {
        "session_id": "sess_001"
    }
    ```
    """
    # 从中间件设置的 state 中获取认证信息
    auth_info = getattr(http_request.state, "auth_info", {})
    app_name = auth_info.get("app_name", "")

    result = await rule_engine_service.get_step_result(
        session_id=request.session_id,
        app_name=app_name
    )

    if not result:
        raise HTTPException(status_code=404, detail=f"Session '{request.session_id}' not found")

    return Success(data=result)
