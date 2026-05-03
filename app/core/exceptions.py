"""
全局异常处理模块

参考 FastAPI 最佳实践，实现统一的异常处理和日志记录
"""
import traceback
from typing import Any, Dict, Optional, Type, Union

from fastapi.exceptions import (
    HTTPException,
    RequestValidationError,
    ResponseValidationError,
)
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from tortoise.exceptions import DoesNotExist, IntegrityError, OperationalError

from app.log import logger, get_request_id


class SettingNotFound(Exception):
    """配置未找到异常"""
    pass


class BusinessException(Exception):
    """业务异常基类"""
    def __init__(self, code: int = 400, msg: str = "业务错误", data: Any = None):
        self.code = code
        self.msg = msg
        self.data = data
        super().__init__(msg)


class PermissionDeniedException(BusinessException):
    """权限不足异常"""
    def __init__(self, msg: str = "权限不足"):
        super().__init__(code=403, msg=msg)


class ResourceNotFoundException(BusinessException):
    """资源不存在异常"""
    def __init__(self, msg: str = "资源不存在"):
        super().__init__(code=404, msg=msg)


class ValidationException(BusinessException):
    """数据验证异常"""
    def __init__(self, msg: str = "数据验证失败"):
        super().__init__(code=422, msg=msg)


def _log_exception(
    request: Request,
    exc: Exception,
    level: str = "error",
    extra: Optional[Dict[str, Any]] = None
) -> None:
    """
    记录异常日志
    
    Args:
        request: 请求对象
        exc: 异常对象
        level: 日志级别 (error, warning, info)
        extra: 额外信息
    """
    log_data = {
        "request_id": get_request_id(),
        "method": request.method,
        "path": request.url.path,
        "query": str(request.query_params),
        "client_ip": request.client.host if request.client else "unknown",
        "exception_type": type(exc).__name__,
        "exception_msg": str(exc),
        "traceback": traceback.format_exc(),
    }
    
    if extra:
        log_data.update(extra)
    
    # 使用 logger.bind() 绑定上下文数据
    bound_logger = logger.bind(**log_data)
    log_msg = f"[Exception] {type(exc).__name__}: {str(exc)}"
    
    if level == "warning":
        bound_logger.warning(log_msg)
    elif level == "info":
        bound_logger.info(log_msg)
    else:
        bound_logger.error(log_msg)


def _make_response(
    code: int,
    msg: str,
    data: Any = None,
    status_code: int = 200,
    request_id: Optional[str] = None
) -> JSONResponse:
    """
    构建统一的错误响应
    
    Args:
        code: 业务错误码
        msg: 错误消息
        data: 附加数据
        status_code: HTTP 状态码
        request_id: 请求追踪ID
    
    Returns:
        JSONResponse: 统一格式的 JSON 响应
    """
    content: Dict[str, Any] = {
        "code": code,
        "msg": msg,
    }
    
    if data is not None:
        content["data"] = data
    
    if request_id:
        content["request_id"] = request_id
    
    return JSONResponse(content=content, status_code=status_code)


# ==================== 具体异常处理器 ====================

async def DoesNotExistHandle(req: Request, exc: DoesNotExist) -> JSONResponse:
    """处理数据库记录不存在异常"""
    _log_exception(req, exc, level="warning")
    return _make_response(
        code=404,
        msg=f"资源不存在: {exc}",
        status_code=404,
        request_id=get_request_id()
    )


async def IntegrityHandle(req: Request, exc: IntegrityError) -> JSONResponse:
    """处理数据库完整性错误"""
    _log_exception(req, exc, level="error")
    return _make_response(
        code=500,
        msg=f"数据完整性错误: {exc}",
        status_code=500,
        request_id=get_request_id()
    )


async def OperationalErrorHandle(req: Request, exc: OperationalError) -> JSONResponse:
    """处理数据库操作错误"""
    _log_exception(req, exc, level="error")
    return _make_response(
        code=500,
        msg=f"数据库操作失败: {exc}",
        status_code=500,
        request_id=get_request_id()
    )


async def HttpExcHandle(req: Request, exc: HTTPException) -> JSONResponse:
    """处理 HTTP 异常"""
    # 4xx 错误记录为 warning，5xx 记录为 error
    level = "warning" if exc.status_code < 500 else "error"
    _log_exception(req, exc, level=level)
    return _make_response(
        code=exc.status_code,
        msg=exc.detail,
        status_code=exc.status_code,
        request_id=get_request_id()
    )


async def StarletteHttpExcHandle(req: Request, exc: StarletteHTTPException) -> JSONResponse:
    """处理 Starlette HTTP 异常"""
    level = "warning" if exc.status_code < 500 else "error"
    _log_exception(req, exc, level=level)
    return _make_response(
        code=exc.status_code,
        msg=exc.detail,
        status_code=exc.status_code,
        request_id=get_request_id()
    )


async def RequestValidationHandle(req: Request, exc: RequestValidationError) -> JSONResponse:
    """处理请求参数验证错误"""
    _log_exception(req, exc, level="warning")
    
    # 提取详细的验证错误信息
    errors = []
    for error in exc.errors():
        error_msg = {
            "field": ".".join(str(x) for x in error.get("loc", [])),
            "msg": error.get("msg", ""),
            "type": error.get("type", ""),
        }
        errors.append(error_msg)
    
    return _make_response(
        code=422,
        msg="请求参数验证失败",
        data={"errors": errors},
        status_code=422,
        request_id=get_request_id()
    )


async def ResponseValidationHandle(req: Request, exc: ResponseValidationError) -> JSONResponse:
    """处理响应数据验证错误"""
    _log_exception(req, exc, level="error")
    return _make_response(
        code=500,
        msg=f"响应数据验证失败: {exc}",
        status_code=500,
        request_id=get_request_id()
    )


async def BusinessExceptionHandle(req: Request, exc: BusinessException) -> JSONResponse:
    """处理业务异常"""
    level = "warning" if exc.code < 500 else "error"
    _log_exception(req, exc, level=level)
    return _make_response(
        code=exc.code,
        msg=exc.msg,
        data=exc.data,
        status_code=exc.code,
        request_id=get_request_id()
    )


async def SettingNotFoundHandle(req: Request, exc: SettingNotFound) -> JSONResponse:
    """处理配置未找到异常"""
    _log_exception(req, exc, level="error")
    return _make_response(
        code=500,
        msg=f"系统配置错误: {exc}",
        status_code=500,
        request_id=get_request_id()
    )


async def GlobalExceptionHandle(req: Request, exc: Exception) -> JSONResponse:
    """
    全局异常处理器 - 捕获所有未处理的异常
    
    这是最后的兜底处理器，确保任何异常都不会暴露敏感信息给客户端
    """
    _log_exception(req, exc, level="error")
    
    # 生产环境不返回详细的异常信息
    from app.settings.config import settings
    if settings.DEBUG:
        msg = f"服务器内部错误: {str(exc)}"
    else:
        msg = "服务器内部错误，请稍后重试"
    
    return _make_response(
        code=500,
        msg=msg,
        status_code=500,
        request_id=get_request_id()
    )
