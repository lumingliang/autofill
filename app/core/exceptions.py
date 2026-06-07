"""
全局异常处理模块 - 统一异常处理和日志记录
异常只在此处记录一次，避免重复日志

支持多应用日志：
- 内部 API (/api/v1/*) 日志写入 app-internal.log
- Open API (/api/v1/open/*) 日志写入 app-open.log
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

from app.log import logger, get_request_id, set_app_type
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


def _get_exception_location(exc_info) -> Optional[str]:
    """获取异常发生的位置（业务代码中的位置）"""
    if not exc_info or exc_info[2] is None:
        return None

    tb = exc_info[2]
    last_business_frame = None

    # 需要排除的路径前缀（第三方库、框架内部）
    skip_prefixes = (
        '/site-packages/',
        'lib/python',
        '/usr/lib/python',
    )

    # 项目内部但非业务代码的路径
    framework_paths = (
        '/app/core/middlewares.py',
        '/app/core/exceptions.py',
        '/app/log/',
        '/app/core/dependencies.py',
        '/app/db/',
    )

    # 遍历整个 traceback 链，找到最底层的业务代码帧
    while tb:
        filename = tb.tb_frame.f_code.co_filename
        lineno = tb.tb_lineno
        function_name = tb.tb_frame.f_code.co_name

        # 排除第三方库和Python标准库
        if any(p in filename for p in skip_prefixes):
            tb = tb.tb_next
            continue

        # 排除框架内部代码，但只针对 /app/ 目录下的
        if '/app/' in filename and any(p in filename for p in framework_paths):
            tb = tb.tb_next
            continue

        # 记录业务代码帧（继续遍历以找到最底层的）
        last_business_frame = (filename, lineno, function_name)
        tb = tb.tb_next

    # 返回最底层的业务代码位置
    if last_business_frame:
        return f"{last_business_frame[0]}:{last_business_frame[1]} in {last_business_frame[2]}()"

    # 如果没有找到业务代码位置，返回 None（而不是返回框架代码）
    return None


def _build_concise_traceback(exc_info) -> str:
    """构建精简的 traceback（只包含业务代码）"""
    tb = exc_info[2]
    tb_lines = []

    # 需要排除的路径前缀（第三方库、框架内部）
    skip_prefixes = (
        '/site-packages/',
        'lib/python',
        '/usr/lib/python',
    )

    # 项目内部但非业务代码的路径
    framework_paths = (
        '/app/core/middlewares.py',
        '/app/core/exceptions.py',
        '/app/log/',
        '/app/core/dependencies.py',
        '/app/db/',
    )

    while tb:
        filename = tb.tb_frame.f_code.co_filename
        lineno = tb.tb_lineno
        function_name = tb.tb_frame.f_code.co_name

        # 排除第三方库和Python标准库
        if any(p in filename for p in skip_prefixes):
            tb = tb.tb_next
            continue

        # 排除框架内部代码，但只针对 /app/ 目录下的
        if '/app/' in filename and any(p in filename for p in framework_paths):
            tb = tb.tb_next
            continue

        # 记录业务代码帧
        if '/app/' in filename:
            short_filename = filename[filename.find('/app/'):]
        else:
            short_filename = filename
        tb_lines.append(f'  File "{short_filename}", line {lineno}, in {function_name}')

        tb = tb.tb_next

    exc_type = exc_info[0].__name__ if exc_info[0] else "Exception"
    exc_msg = str(exc_info[1]) if exc_info[1] else ""

    return f"{exc_type}: {exc_msg}\n" + "\n".join(tb_lines) if tb_lines else f"{exc_type}: {exc_msg}"


def _set_app_type_from_path(path: str):
    """根据请求路径设置应用类型"""
    if path.startswith("/api/v1/open/"):
        set_app_type("open")
    else:
        set_app_type("internal")


def _log_exception(
    request: Request,
    exc: Exception,
    level: str = "error",
) -> None:
    """
    记录异常日志到对应应用的日志文件

    根据请求路径自动判断应用类型：
    - /api/v1/open/* -> Open API 日志
    - 其他 -> 内部 API 日志
    """
    # 设置应用类型（logger 会自动分流到对应文件）
    path = str(request.url.path)
    _set_app_type_from_path(path)

    # 获取异常信息
    exc_type = type(exc).__name__
    exc_msg = str(exc)
    exc_info = sys.exc_info()
    location = _get_exception_location(exc_info)
    concise_traceback = _build_concise_traceback(exc_info)

    # 构建日志数据
    log_data = {
        "event": "exception",
        "method": request.method,
        "path": path,
        "exception_type": exc_type,
        "exception_msg": exc_msg,
        "location": location,
        "traceback": concise_traceback,
    }

    # 记录异常日志
    if level == "warning":
        logger.warning(**log_data)
    else:
        logger.error(**log_data)


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
        msg=f"配置未找到: {exc}",
        status_code=500,
    )


async def PermissionDeniedHandle(req: Request, exc: PermissionDeniedException) -> JSONResponse:
    """处理权限不足异常"""
    _log_exception(req, exc, level="warning")
    return _make_response(
        code=403,
        msg=exc.msg,
        status_code=403,
    )


async def ResourceNotFoundHandle(req: Request, exc: ResourceNotFoundException) -> JSONResponse:
    """处理资源不存在异常"""
    _log_exception(req, exc, level="warning")
    return _make_response(
        code=404,
        msg=exc.msg,
        status_code=404,
    )


async def ValidationHandle(req: Request, exc: ValidationException) -> JSONResponse:
    """处理数据验证异常"""
    _log_exception(req, exc, level="warning")
    return _make_response(
        code=422,
        msg=exc.msg,
        status_code=422,
    )


async def AllExceptionHandle(req: Request, exc: Exception) -> JSONResponse:
    """处理所有未捕获的异常"""
    _log_exception(req, exc, level="error")
    return _make_response(
        code=500,
        msg=f"服务器内部错误: {str(exc)}",
        status_code=500,
    )
