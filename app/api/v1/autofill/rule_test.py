"""
规则执行测试接口（前端页面使用）

参考 depts.py 简洁风格：
- 直接在路由函数中调用 Service 层
- 不使用 API 类包装
- 认证由中间件统一处理
"""
import json
import uuid

from fastapi import APIRouter, Query, Request
from fastapi.exceptions import HTTPException

from app.schemas.base import Fail, Success, SuccessExtra
from app.services.autofill.app_service import app_service
from app.services.autofill.rule_engine_service import rule_engine_service
from app.services.rule_management.rule_service import rule_service
from app.log import logger

router = APIRouter()


@router.get("/rule_test/apps", summary="获取应用列表")
async def list_apps_for_test(
    request: Request,
):
    """获取当前用户可用的应用列表（用于规则测试页面下拉选择）"""
    current_user = request.state.current_user if hasattr(request.state, 'current_user') else None

    if not current_user:
        return Fail(code=401, msg="用户未认证")

    # 租户过滤由 Repository 层自动处理
    total, apps = await app_service.list_all_apps(
        page=1,
        page_size=1000
    )

    data = []
    for app in apps:
        data.append({
            "app_name": app.app_name,
            "tenant_id": app.tenant_id
        })

    return Success(data=data)


@router.get("/rule_test/rules", summary="获取规则列表")
async def list_rules_for_test(
    request: Request,
    app_name: str = Query(..., description="应用名称"),
):
    """获取指定应用下的规则列表（用于规则测试页面下拉选择）"""
    _, rules = await rule_service.list_rules(
        app_name=app_name,
        page=1,
        page_size=1000
    )

    data = []
    for rule in rules:
        data.append({
            "id": rule.id,
            "rule_code": rule.rule_code,
            "rule_name": rule.rule_name,
            "status": rule.status
        })

    return Success(data=data)


@router.get("/rule_test/rule_columns", summary="获取规则CSV表头")
async def get_rule_columns(
    request: Request,
    rule_code: str = Query(..., description="规则编码"),
    app_name: str = Query(..., description="应用名称"),
):
    """获取指定规则的CSV表头（用于前端多选下拉）"""
    rule = await rule_service.get_rule_by_code(
        rule_code=rule_code,
        app_name=app_name
    )

    if not rule:
        return Fail(code=404, msg="规则不存在")

    if not rule.latest_version_id:
        return Fail(code=404, msg="规则没有版本数据")

    version = await rule_service.get_version_by_id(version_id=rule.latest_version_id)
    if not version:
        return Fail(code=404, msg="规则版本不存在")

    try:
        content_json = await rule_service.get_content_json(version)
        if not content_json:
            return Success(data={"columns": [], "sample_data": []})

        headers = content_json.get("headers", [])
        data = content_json.get("data", [])

        sample_data = data[:3] if data else []

        return Success(data={
            "columns": headers,
            "sample_data": sample_data,
            "rule_code": rule_code,
            "rule_name": rule.rule_name
        })

    except Exception as e:
        logger.error(f"解析CSV失败: {e}")
        return Fail(code=500, msg=f"解析CSV失败: {str(e)}")


@router.post("/rule_test/execute", summary="执行规则测试")
async def execute_rule_test(
    request: Request,
):
    """
    前端规则测试页面调用此接口执行规则测试

    请求示例:
    ```json
    {
        "app_name": "customer_service",
        "query": "我买的手机屏幕碎了，我要投诉",
        "params": [
            {
                "rule_name": "event_type",
                "prompt": {
                    "type": "choice",
                    "filter": {"一级事件类型": "投诉"},
                    "select_fields": ["二级事件类型id", "三级事件类型id"],
                    "name_fields": ["二级事件类型", "三级事件类型"],
                    "rule_fields": ["二级事件类型填写规则", "三级事件类型填写规则"]
                }
            }
        ]
    }
    ```
    """
    request_data = await request.json()

    app_name = request_data.get("app_name")
    query = request_data.get("query")
    params = request_data.get("params", [])
    temperature = request_data.get("temperature", 0.7)
    system_prompt_name = request_data.get("system_prompt_name")

    if not app_name:
        raise HTTPException(status_code=400, detail="app_name is required")

    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    if not params:
        raise HTTPException(status_code=400, detail="params is required")

    for i, param in enumerate(params):
        if not param.get("rule_name"):
            raise HTTPException(status_code=400, detail=f"params[{i}].rule_name is required")
        if not param.get("prompt"):
            raise HTTPException(status_code=400, detail=f"params[{i}].prompt is required")

    method = "json_parser" if len(params) > 1 else "plain"

    session_id = f"test_{uuid.uuid4().hex[:16]}"

    logger.info(
        f"Rule test execute: session_id={session_id}, app_name={app_name}, "
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
            step=1,
            is_last=True,
            system_prompt_name=system_prompt_name
        )

        return Success(data=result)

    except ValueError as e:
        logger.error(f"Rule test validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Rule test error: {e}")
        raise HTTPException(status_code=500, detail=f"Rule execution failed: {str(e)}")


@router.post("/rule_test/export_curl", summary="导出规则测试Curl命令")
async def export_rule_test_curl(
    request: Request,
):
    """
    根据前端配置生成可直接测试的curl命令

    请求示例:
    ```json
    {
        "app_name": "customer_service",
        "query": "我买的手机屏幕碎了，我要投诉",
        "params": [
            {
                "rule_name": "event_type",
                "prompt": {
                    "type": "choice",
                    "filter": {"一级事件类型": "投诉"},
                    "select_fields": ["二级事件类型id", "三级事件类型id"],
                    "name_fields": ["二级事件类型", "三级事件类型"],
                    "rule_fields": ["二级事件类型填写规则", "三级事件类型填写规则"]
                }
            }
        ]
    }
    ```
    """
    request_data = await request.json()

    app_name = request_data.get("app_name")
    query = request_data.get("query")
    params = request_data.get("params", [])
    temperature = request_data.get("temperature", 0.7)
    system_prompt_name = request_data.get("system_prompt_name")

    if not app_name:
        raise HTTPException(status_code=400, detail="app_name is required")

    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    if not params:
        raise HTTPException(status_code=400, detail="params is required")

    for i, param in enumerate(params):
        if not param.get("rule_name"):
            raise HTTPException(status_code=400, detail=f"params[{i}].rule_name is required")
        if not param.get("prompt"):
            raise HTTPException(status_code=400, detail=f"params[{i}].prompt is required")

    # 租户过滤由 Repository 层自动处理
    app = await app_service.get_app_by_name_for_current_tenant(
        app_name=app_name
    )

    if not app:
        raise HTTPException(status_code=400, detail=f"应用 '{app_name}' 不存在")

    method = "json_parser" if len(params) > 1 else "plain"

    session_id = f"test_{uuid.uuid4().hex[:16]}"

    execute_request_body = {
        "session_id": session_id,
        "query": query,
        "method": method,
        "temperature": temperature,
        "step": 1,
        "is_last": True,
        "params": params
    }

    if system_prompt_name:
        execute_request_body["system_prompt_name"] = system_prompt_name

    base_url = str(request.base_url).rstrip('/')
    api_endpoint = f"{base_url}/api/autofill/llm/rule/execute"

    json_body = json.dumps(execute_request_body, ensure_ascii=False, indent=2)

    api_key = app.api_key if app and app.api_key else 'your_api_key_here'

    curl_command = f"""curl -X POST '{api_endpoint}' \\
  -H 'Content-Type: application/json' \\
  -H 'Authorization: Bearer {api_key}' \\
  -d '{json_body}'"""

    logger.info(
        f"Rule test curl exported: session_id={session_id}, app_name={app_name}, "
        f"tenant_id={effective_tenant_id}, method={method}"
    )

    return Success(data={
        "curl_command": curl_command,
        "api_endpoint": "/api/autofill/llm/rule/execute",
        "method": "POST",
        "request_body": execute_request_body,
        "description": "可直接在终端执行的curl命令，用于测试规则引擎API"
    })
