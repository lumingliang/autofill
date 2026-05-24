"""
规则执行测试接口（前端页面使用）
提供应用列表、规则列表、CSV表头获取和规则执行测试功能

注意：超管使用请求的tenant_id，普通用户使用ctx的tenant_id
"""
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, Query, Request
from fastapi.exceptions import HTTPException
from tortoise.expressions import Q

from app.controllers.rule_management import rule_info_controller, rule_version_controller
from app.core.dependency import AuthControl, build_tenant_query
from app.models.autofill import AppManagement
from app.models.rule_management import RuleInfo, RuleVersion
from app.schemas.base import Fail, Success, SuccessExtra
from app.services.autofill.rule_engine_service import rule_engine_service
from app.services.rule_management.rule_service import rule_service
from app.log import logger

router = APIRouter()


def is_superuser(user) -> bool:
    """判断用户是否为超级管理员"""
    return getattr(user, 'is_superuser', False) or getattr(user, 'role', 0) == 0


@router.get("/rule_test/apps", summary="获取应用列表")
async def list_apps_for_test(
    token: str = Header(..., description="token验证"),
):
    """获取当前用户可用的应用列表（用于规则测试页面下拉选择）

    超管可以查看所有应用，普通用户只能查看自己租户的应用
    """
    current_user = await AuthControl.is_authed(token)

    # 构建租户查询条件
    tenant_query = build_tenant_query(current_user, 0)
    effective_tenant_id = tenant_query.get("tenant_id", 0)

    q = Q()
    if effective_tenant_id > 0:
        q &= Q(tenant_id=effective_tenant_id)

    apps = await AppManagement.filter(q).all()

    data = []
    for app in apps:
        # 检查应用是否配置了Dify API Key
        has_api_key = bool(app.dify_api_key)

        data.append({
            "app_name": app.app_name,
            "tenant_id": app.tenant_id,
            "has_api_key": has_api_key,
            "api_key": app.dify_api_key if has_api_key else None
        })

    return Success(data=data)


@router.get("/rule_test/rules", summary="获取规则列表")
async def list_rules_for_test(
    app_name: str = Query(..., description="应用名称"),
    tenant_id: Optional[int] = Query(None, description="租户ID（仅超管可用）"),
    token: str = Header(..., description="token验证"),
):
    """获取指定应用下的规则列表（用于规则测试页面下拉选择）

    超管可以通过tenant_id参数指定租户，普通用户使用当前用户的租户
    """
    current_user = await AuthControl.is_authed(token)

    # 确定有效租户ID：超管使用请求的tenant_id，普通用户使用ctx的tenant_id
    if is_superuser(current_user) and tenant_id is not None:
        effective_tenant_id = tenant_id
    else:
        tenant_query = build_tenant_query(current_user, 0)
        effective_tenant_id = tenant_query.get("tenant_id", 0)

    q = Q(app_name=app_name, deleted=0)
    if effective_tenant_id > 0:
        q &= Q(tenant_id=effective_tenant_id)

    rules = await RuleInfo.filter(q).all()

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
    rule_code: str = Query(..., description="规则编码"),
    app_name: str = Query(..., description="应用名称"),
    tenant_id: Optional[int] = Query(None, description="租户ID（仅超管可用）"),
    token: str = Header(..., description="token验证"),
):
    """获取指定规则的CSV表头（用于前端多选下拉）

    超管可以通过tenant_id参数指定租户，普通用户使用当前用户的租户
    """
    current_user = await AuthControl.is_authed(token)

    # 确定有效租户ID：超管使用请求的tenant_id，普通用户使用ctx的tenant_id
    if is_superuser(current_user) and tenant_id is not None:
        effective_tenant_id = tenant_id
    else:
        tenant_query = build_tenant_query(current_user, 0)
        effective_tenant_id = tenant_query.get("tenant_id", 0)

    # 查询规则
    q = Q(rule_code=rule_code, app_name=app_name, deleted=0)
    if effective_tenant_id > 0:
        q &= Q(tenant_id=effective_tenant_id)

    rule = await RuleInfo.filter(q).first()

    if not rule:
        return Fail(code=404, msg="规则不存在")

    # 获取最新版本
    if not rule.latest_version_id:
        return Fail(code=404, msg="规则没有版本数据")

    version = await RuleVersion.filter(id=rule.latest_version_id, deleted=0).first()
    if not version:
        return Fail(code=404, msg="规则版本不存在")

    # 解析CSV获取表头
    try:
        # 使用rule_service获取内容
        content_json = await rule_service._get_content_json(version)
        if not content_json:
            return Success(data={"columns": [], "sample_data": []})

        # content_json格式: {"headers": [...], "data": [[...], [...]]}
        headers = content_json.get("headers", [])
        data = content_json.get("data", [])

        # 获取前3行作为示例数据
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
    token: str = Header(..., description="token验证"),
):
    """
    前端规则测试页面调用此接口执行规则测试

    超管可以通过tenant_id参数指定租户，普通用户使用当前用户的租户

    请求示例:
    ```json
    {
        "app_name": "customer_service",
        "query": "我买的手机屏幕碎了，我要投诉",
        "tenant_id": 1,  // 仅超管可用
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
    current_user = await AuthControl.is_authed(token)

    # 解析请求体
    request_data = await request.json()

    app_name = request_data.get("app_name")
    query = request_data.get("query")
    params = request_data.get("params", [])
    temperature = request_data.get("temperature", 0.7)
    request_tenant_id = request_data.get("tenant_id")

    # 确定有效租户ID：超管使用请求的tenant_id，普通用户使用ctx的tenant_id
    if is_superuser(current_user) and request_tenant_id is not None:
        effective_tenant_id = request_tenant_id
    else:
        tenant_query = build_tenant_query(current_user, 0)
        effective_tenant_id = tenant_query.get("tenant_id", 0)

    if not app_name:
        raise HTTPException(status_code=400, detail="app_name is required")

    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    if not params:
        raise HTTPException(status_code=400, detail="params is required")

    # 验证params格式
    for i, param in enumerate(params):
        if not param.get("rule_name"):
            raise HTTPException(status_code=400, detail=f"params[{i}].rule_name is required")
        if not param.get("prompt"):
            raise HTTPException(status_code=400, detail=f"params[{i}].prompt is required")

    # 获取应用的API Key（从AppManagement表中查询）
    app = await AppManagement.filter(
        tenant_id=effective_tenant_id,
        app_name=app_name
    ).first()

    if not app or not app.dify_api_key:
        raise HTTPException(status_code=400, detail=f"应用 '{app_name}' 未配置Dify API Key")

    # 智能method适配：多任务默认json_parser，单任务默认plain
    method = "json_parser" if len(params) > 1 else "plain"

    # 生成session_id
    session_id = f"test_{uuid.uuid4().hex[:16]}"

    logger.info(
        f"Rule test execute: session_id={session_id}, app_name={app_name}, "
        f"tenant_id={effective_tenant_id}, method={method}, params_count={len(params)}"
    )

    try:
        result = await rule_engine_service.execute_rule(
            tenant_id=effective_tenant_id,
            app_name=app_name,
            session_id=session_id,
            query=query,
            method=method,
            temperature=temperature,
            params=params,
            step=1,
            is_last=True
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
    token: str = Header(..., description="token验证"),
):
    """
    根据前端配置生成可直接测试的curl命令

    请求示例:
    ```json
    {
        "app_name": "customer_service",
        "query": "我买的手机屏幕碎了，我要投诉",
        "tenant_id": 1,  // 仅超管可用
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

    响应示例:
    ```json
    {
        "code": 200,
        "msg": "success",
        "data": {
            "curl_command": "curl -X POST 'http://localhost:9999/api/autofill/llm/rule/execute' -H 'Content-Type: application/json' -H 'Authorization: Bearer xxx' -d '{...}'",
            "api_endpoint": "/api/autofill/llm/rule/execute",
            "method": "POST",
            "request_body": {...}
        }
    }
    ```
    """
    current_user = await AuthControl.is_authed(token)

    # 解析请求体
    request_data = await request.json()

    app_name = request_data.get("app_name")
    query = request_data.get("query")
    params = request_data.get("params", [])
    temperature = request_data.get("temperature", 0.7)
    request_tenant_id = request_data.get("tenant_id")

    # 确定有效租户ID：超管使用请求的tenant_id，普通用户使用ctx的tenant_id
    if is_superuser(current_user) and request_tenant_id is not None:
        effective_tenant_id = request_tenant_id
    else:
        tenant_query = build_tenant_query(current_user, 0)
        effective_tenant_id = tenant_query.get("tenant_id", 0)

    if not app_name:
        raise HTTPException(status_code=400, detail="app_name is required")

    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    if not params:
        raise HTTPException(status_code=400, detail="params is required")

    # 验证params格式
    for i, param in enumerate(params):
        if not param.get("rule_name"):
            raise HTTPException(status_code=400, detail=f"params[{i}].rule_name is required")
        if not param.get("prompt"):
            raise HTTPException(status_code=400, detail=f"params[{i}].prompt is required")

    # 获取应用的API Key（从AppManagement表中查询）
    app = await AppManagement.filter(
        tenant_id=effective_tenant_id,
        app_name=app_name
    ).first()

    if not app or not app.dify_api_key:
        raise HTTPException(status_code=400, detail=f"应用 '{app_name}' 未配置Dify API Key")

    # 智能method适配：多任务默认json_parser，单任务默认plain
    method = "json_parser" if len(params) > 1 else "plain"

    # 生成session_id
    session_id = f"test_{uuid.uuid4().hex[:16]}"

    # 构建与 rule_engine_service.execute_rule 相同的请求体
    execute_request_body = {
        "session_id": session_id,
        "query": query,
        "method": method,
        "temperature": temperature,
        "step": 1,
        "is_last": True,
        "params": params
    }

    # 构建curl命令 - 使用应用的API Key（不是Dify API Key）
    import json
    base_url = str(request.base_url).rstrip('/')
    api_endpoint = f"{base_url}/api/autofill/llm/rule/execute"

    # 转义JSON中的单引号，以便在shell中使用
    json_body = json.dumps(execute_request_body, ensure_ascii=False, indent=2)

    # 使用应用的API Key作为Authorization（用于认证应用身份）
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
