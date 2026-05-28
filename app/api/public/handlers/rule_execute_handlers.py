"""
规则执行引擎接口
提供基于CSV规则的选择题和填空题执行能力
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException

from app.core.autofill_auth import APIKeyAuth
from app.log import logger
from app.schemas.base import Fail, Success
from app.services.autofill.rule_engine_service import rule_engine_service

router = APIRouter()


class RuleExecuteRequest:
    """规则执行请求"""
    def __init__(
        self,
        session_id: str,
        query: str,
        method: str = "plain",
        temperature: float = 0.7,
        step: int = 1,
        is_last: bool = False,
        params: List[Dict[str, Any]] = None
    ):
        self.session_id = session_id
        self.query = query
        self.method = method
        self.temperature = temperature
        self.step = step
        self.is_last = is_last
        self.params = params or []


class RuleExecuteResultRequest:
    """规则执行结果查询请求"""
    def __init__(self, session_id: str):
        self.session_id = session_id


@router.post("/autofill/llm/rule/execute", summary="规则执行引擎")
async def execute_rule(
    request_data: Dict[str, Any],
    auth_info: dict = Depends(APIKeyAuth.authenticate)
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
    app_name = auth_info["app_name"]

    # 参数验证
    session_id = request_data.get("session_id")
    query = request_data.get("query")
    temperature = request_data.get("temperature", 0.7)
    step = request_data.get("step", 1)
    is_last = request_data.get("is_last", False)
    params = request_data.get("params", [])
    system_prompt = request_data.get("system_prompt")  # 新增：自定义系统提示词
    system_prompt_name = request_data.get("system_prompt_name")  # 新增：系统提示词名称

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    if not params:
        raise HTTPException(status_code=400, detail="params is required")

    # 智能method适配：多任务默认json_parser，单任务默认plain
    method = request_data.get("method")
    if not method:
        method = "json_parser" if len(params) > 1 else "plain"

    # 验证params格式
    for i, param in enumerate(params):
        if not param.get("rule_name"):
            raise HTTPException(status_code=400, detail=f"params[{i}].rule_name is required")
        if not param.get("prompt"):
            raise HTTPException(status_code=400, detail=f"params[{i}].prompt is required")

    logger.info(
        f"Rule execute: session_id={session_id}, step={step}, is_last={is_last}, "
        f"method={method}, params_count={len(params)}"
    )

    try:
        result = await rule_engine_service.execute_rule(
            app_name=app_name,
            session_id=session_id,
            query=query,
            method=method,
            temperature=temperature,
            params=params,
            step=step,
            is_last=is_last,
            system_prompt=system_prompt,
            system_prompt_name=system_prompt_name
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
    request_data: Dict[str, Any],
    auth_info: dict = Depends(APIKeyAuth.authenticate)
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
    app_name = auth_info["app_name"]
    session_id = request_data.get("session_id")

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    result = await rule_engine_service.get_step_result(
        session_id=session_id,
        app_name=app_name
    )

    if not result:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return Success(data=result)
