"""
全局异常处理模块 - 统一异常处理和日志记录
异常只在此处记录一次，避免重复日志
"""
import sys
from typing import Any, Dict, Optional

from fastapi.exceptions import (
    HTTPException,
    RequestValidationError,
    ResponseValidationError,
)
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from tortoise.exceptions import DoesNotExist, IntegrityError, OperationalError

from app.log import logger, get_request_id, get_exception_location, set_request_logged
from app.settings.config import settings


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


def _extract_location_from_validation_error(exc: RequestValidationError) -> Optional[str]:
    """从 RequestValidationError 中提取业务代码位置"""
    import re
    
    exc_str = str(exc)
    # 匹配格式: File "/path/to/file.py", line XX, in function_name
    match = re.search(r'File "([^"]+)", line (\d+)', exc_str)
    if match:
        return f"{match.group(1)}:{match.group(2)}"
    return None


def _log_exception(
    request: Request,
    exc: Exception,
    level: str = "error",
) -> None:
    """
    统一记录异常日志 - 只在异常处理器中调用一次
    注意：此函数不再直接记录日志，而是将异常信息存入请求上下文
    由中间件统一记录，避免重复日志
    """
    # 不再记录日志，由中间件统一处理
    # 异常信息会通过响应体返回给客户端
    pass


def _make_response(
    code: int,
    msg: str,
    data: Any = None,
    status_code: int = 200,
) -> JSONResponse:
    """构建统一的错误响应"""
    content: Dict[str, Any] = {
        "code": code,
        "msg": msg,
    }

    if data is not None:
        content["data"] = data

    request_id = get_request_id()
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
    )


async def IntegrityHandle(req: Request, exc: IntegrityError) -> JSONResponse:
    """处理数据库完整性错误"""
    _log_exception(req, exc, level="error")
    return _make_response(
        code=500,
        msg=f"数据完整性错误: {exc}",
        status_code=500,
    )


async def OperationalErrorHandle(req: Request, exc: OperationalError) -> JSONResponse:
    """处理数据库操作错误"""
    _log_exception(req, exc, level="error")
    return _make_response(
        code=500,
        msg=f"数据库操作失败: {exc}",
        status_code=500,
    )


async def HttpExcHandle(req: Request, exc: HTTPException) -> JSONResponse:
    """处理 HTTP 异常"""
    level = "warning" if exc.status_code < 500 else "error"
    _log_exception(req, exc, level=level)
    return _make_response(
        code=exc.status_code,
        msg=exc.detail,
        status_code=exc.status_code,
    )


async def StarletteHttpExcHandle(req: Request, exc: StarletteHTTPException) -> JSONResponse:
    """处理 Starlette HTTP 异常"""
    level = "warning" if exc.status_code < 500 else "error"
    _log_exception(req, exc, level=level)
    return _make_response(
        code=exc.status_code,
        msg=exc.detail,
        status_code=exc.status_code,
    )


async def RequestValidationHandle(req: Request, exc: RequestValidationError) -> JSONResponse:
    """处理请求参数验证错误"""
    _log_exception(req, exc, level="warning")

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
    )


async def ResponseValidationHandle(req: Request, exc: ResponseValidationError) -> JSONResponse:
    """处理响应数据验证错误"""
    _log_exception(req, exc, level="error")
    return _make_response(
        code=500,
        msg=f"响应数据验证失败: {exc}",
        status_code=500,
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
    )


async def SettingNotFoundHandle(req: Request, exc: SettingNotFound) -> JSONResponse:
    """处理配置未找到异常"""
    _log_exception(req, exc, level="error")
    return _make_response(
        code=500,
        msg=f"系统配置错误: {exc}",
        status_code=500,
    )


async def GlobalExceptionHandle(req: Request, exc: Exception) -> JSONResponse:
    """
    全局异常处理器 - 捕获所有未处理的异常
    这是最后的兜底处理器
    """
    _log_exception(req, exc, level="error")

    if settings.DEBUG:
        msg = f"服务器内部错误: {str(exc)}"
    else:
        msg = "服务器内部错误，请稍后重试"

    return _make_response(
        code=500,
        msg=msg,
        status_code=500,
    )
