"""
测试填单接口（供前端调用）
使用 JWT Token 认证
"""
from typing import List, Optional

from fastapi import APIRouter, Header
from pydantic import BaseModel

from app.core.dependency import AuthControl
from app.schemas.base import Success
from app.services.autofill.test_fill_service import test_fill_service

router = APIRouter()


class ChatSessionRequest(BaseModel):
    """聊天会话请求"""
    session_id: Optional[str] = None
    system_prompt: Optional[str] = None
    message: str
    clear_history: bool = False


class TestFillRequest(BaseModel):
    """测试填单请求 - 新格式：直接使用名称而非ID"""
    app_name: str
    group_names: List[str]
    field_names: List[str] = []
    system_prompt_group: Optional[str] = None
    chat_record: str
    tenant_id: Optional[int] = None  # 超级用户可传递租户ID


@router.post("/test-fill/chat", summary="聊天会话")
async def chat_session(
    request: ChatSessionRequest,
    token: str = Header(..., description="token验证"),
):
    """
    聊天会话接口，支持多轮对话
    用于生成客服与用户的对话记录
    """
    current_user = await AuthControl.is_authed(token)

    result = await test_fill_service.chat_session(
        tenant_id=current_user.current_tenant_id or 1,
        app_name="default",
        session_id=request.session_id,
        system_prompt=request.system_prompt,
        message=request.message,
        clear_history=request.clear_history
    )

    return Success(data=result)


@router.post("/test-fill/fill", summary="测试填单")
async def test_fill(
    request: TestFillRequest,
    token: str = Header(..., description="token验证"),
):
    """
    测试填单功能
    根据应用名称、字段组名称列表、字段名称列表和聊天记录进行填单
    直接调用 step_llm_fill_service 进行处理
    """
    current_user = await AuthControl.is_authed(token)

    # 超级用户可以传递tenant_id，普通用户使用JWT中的tenant_id
    tenant_id = request.tenant_id if current_user.is_superuser and request.tenant_id else current_user.current_tenant_id

    result = await test_fill_service.test_fill(
        tenant_id=tenant_id or 1,
        app_name=request.app_name,
        group_names=request.group_names,
        field_names=request.field_names,
        chat_record=request.chat_record
    )

    return Success(data=result)
