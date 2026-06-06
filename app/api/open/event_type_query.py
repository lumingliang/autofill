"""
事件类型分级查询接口

先查询一级事件类型，再根据一级事件类型查询二三级事件类型，最后合并结果返回
"""
import uuid

from fastapi import APIRouter, Request

from app.log import logger
from app.schemas.base import Success
from app.schemas.open.schemas import EventTypeQueryRequest
from app.services.autofill.rule_engine_service import rule_engine_service

router = APIRouter()


def _extract_first_level_event_type(result: dict) -> str:
    """从规则引擎结果中提取一级事件类型

    规则引擎返回结构: {"code": 200, "data": {"一级事件类型": "咨询", "results": {"event_type": {"一级事件类型": "咨询"}}}}
    """
    if not result or not isinstance(result, dict):
        return ""

    if result.get("code") != 200:
        return ""

    data = result.get("data", {})

    # 尝试直接从 data 中获取
    first_level = data.get("一级事件类型", "")
    if first_level:
        return str(first_level).strip()

    # 尝试从 results.event_type 中获取
    results = data.get("results", {})
    event_type = results.get("event_type", {})
    first_level = event_type.get("一级事件类型", "")

    return str(first_level).strip() if first_level else ""


def _extract_second_third_level_result(result: dict) -> str:
    """从规则引擎结果中提取二三级事件类型的分析结果

    规则引擎返回结构: {"code": 200, "data": {"llm_res": "...", "results": {"event_type": {"llm_res": "..."}}}}
    """
    if not result or not isinstance(result, dict):
        return ""

    if result.get("code") != 200:
        return ""

    data = result.get("data", {})

    # 尝试直接从 data 中获取 llm_res
    llm_res = data.get("llm_res", "")
    if llm_res:
        return str(llm_res).strip()

    # 尝试从 results.event_type 中获取
    results = data.get("results", {})
    event_type = results.get("event_type", {})
    llm_res = event_type.get("llm_res", "")

    return str(llm_res).strip() if llm_res else ""


@router.post("/autofill/event-type-query", summary="事件类型分级查询")
async def event_type_query(
    request: EventTypeQueryRequest,
    http_request: Request,
):
    """
    事件类型分级查询接口

    该接口执行两次规则引擎调用：
    1. 第一次：查询一级事件类型（filter 为空）
    2. 第二次：根据一级事件类型查询二三级事件类型

    - **query**: 用户输入的问题描述，如："我的手机坏了"
    - **session_id_prefix**: 会话ID前缀（可选，默认"test"）
    - **temperature**: 温度参数（可选，默认0.7）
    - **system_prompt_name**: 系统提示词名称（可选，默认"测试选择题提示词"）

    返回合并后的结果，包含一级事件类型和二三级事件类型的分析结果
    """
    # 从中间件设置的 state 中获取认证信息
    auth_info = getattr(http_request.state, "auth_info", {})
    app_name = auth_info.get("app_name", "")

    # 生成两个不同的 session_id
    random_num1 = uuid.uuid4().hex[:16]
    random_num2 = uuid.uuid4().hex[:16]
    session_id_first = f"{request.session_id_prefix}_{random_num1}"
    session_id_second = f"{request.session_id_prefix}_{random_num2}"

    logger.info(f"Event type query: query={request.query}, session_id_first={session_id_first}, session_id_second={session_id_second}")

    try:
        # ========== 第一次请求：获取一级事件类型 ==========
        first_result = await rule_engine_service.execute_rule(
            app_name=app_name,
            session_id=session_id_first,
            query=request.query,
            method="plain",
            params=[
                {
                    "rule_name": "event_type",
                    "prompt": {
                        "type": "choice",
                        "filter": {},
                        "select_fields": ["一级事件类型"],
                        "name_fields": ["一级事件类型"],
                        "rule_fields": ["一级事件类型"]
                    }
                }
            ],
            step=1,
            is_last=False,
            system_prompt_name=request.system_prompt_name
        )

        # 提取一级事件类型
        first_level_event_type = _extract_first_level_event_type(first_result)
        logger.info(f"First level event type: {first_level_event_type}")

        if not first_level_event_type:
            logger.warning(f"Failed to extract first level event type from result: {first_result}")

        # ========== 第二次请求：获取二三级事件类型 ==========
        # 使用第一次的结果作为 filter
        second_filter = {}
        if first_level_event_type:
            second_filter = {"一级事件类型": first_level_event_type}

        second_result = await rule_engine_service.execute_rule(
            app_name=app_name,
            session_id=session_id_second,
            query=request.query,
            method="plain",
            params=[
                {
                    "rule_name": "event_type",
                    "prompt": {
                        "type": "choice",
                        "filter": second_filter,
                        "select_fields": ["三级事件类型", "二级事件类型"],
                        "name_fields": ["三级事件类型", "二级事件类型"],
                        "rule_fields": ["三级事件类型", "二级事件类型"]
                    }
                }
            ],
            step=2,
            is_last=True,
            system_prompt_name=request.system_prompt_name
        )

        # 提取二三级事件类型结果
        second_third_level_result = _extract_second_third_level_result(second_result)
        logger.info(f"Second/third level result length: {len(second_third_level_result)}")

        # ========== 合并结果：将两次请求的 data 字段展平，后面的覆盖前面的 ==========
        first_data = first_result.get("data", {}) if isinstance(first_result, dict) else {}
        second_data = second_result.get("data", {}) if isinstance(second_result, dict) else {}
        merged_data = {**first_data, **second_data}

        return Success(data=merged_data)

    except ValueError as e:
        logger.error(f"Event type query validation error: {e}")
        return Success(code=400, message=str(e), data={"query": request.query, "error": str(e)})

    except Exception as e:
        logger.error(f"Event type query error: {e}")
        return Success(code=500, message=f"处理失败: {str(e)}", data={"query": request.query, "error": str(e)})
