"""
统一日志模块 - 基于 structlog 的结构化日志
支持多应用日志自动分流

主要字段：request_id, tenant_id, app, elapsed_time, exception(filename:lineno)

使用方式：
    from app.log import logger
    logger.info("message")  # 自动根据请求路径分流到不同文件

日志文件：
- 内部 API (/api/v1/*)      → app-internal.log
- Open API (/api/v1/open/*) → app-open.log
"""
import inspect
import logging
import sys
from contextvars import ContextVar
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import structlog

from app.settings import settings

# ============ 上下文变量 ============
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
tenant_id_var: ContextVar[int] = ContextVar("tenant_id", default=0)
request_logged_var: ContextVar[bool] = ContextVar("request_logged", default=False)
app_type_var: ContextVar[str] = ContextVar("app_type", default="internal")


# ============ 上下文变量操作函数 ============
def get_request_id() -> str:
    return request_id_var.get()


def set_request_id(request_id: str):
    request_id_var.set(request_id)


def get_tenant_id() -> int:
    return tenant_id_var.get()


def set_tenant_id(tenant_id: int):
    tenant_id_var.set(tenant_id)


def is_request_logged() -> bool:
    """检查当前请求是否已经被记录过日志"""
    return request_logged_var.get()


def set_request_logged(logged: bool = True):
    """设置当前请求的日志记录状态"""
    request_logged_var.set(logged)


def get_app_type() -> str:
    """获取当前应用类型"""
    return app_type_var.get()


def set_app_type(app_type: str):
    """设置当前应用类型 (internal 或 open)"""
    app_type_var.set(app_type)


# ============ 工具函数 ============
def get_exception_location(exc_info):
    """获取异常发生的位置（业务代码中的位置）"""
    if not exc_info or exc_info[2] is None:
        return None

    tb = exc_info[2]
    last_business_frame = None

    skip_prefixes = (
        '/site-packages/',
        'lib/python',
        '/app/core/middlewares.py',
        '/app/core/exceptions.py',
        '/app/log/log.py',
    )

    while tb:
        filename = tb.tb_frame.f_code.co_filename
        lineno = tb.tb_lineno
        function_name = tb.tb_frame.f_code.co_name

        should_skip = any(p in filename for p in skip_prefixes)

        if should_skip:
            tb = tb.tb_next
            continue

        last_business_frame = (filename, lineno, function_name)
        tb = tb.tb_next

    if last_business_frame:
        return f"{last_business_frame[0]}:{last_business_frame[1]} in {last_business_frame[2]}()"

    tb = exc_info[2]
    while tb.tb_next:
        tb = tb.tb_next
    filename = tb.tb_frame.f_code.co_filename
    lineno = tb.tb_lineno
    function_name = tb.tb_frame.f_code.co_name
    return f"{filename}:{lineno} in {function_name}()"


def get_caller_location(skip_frames: int = 2) -> str:
    """获取调用者的文件位置和行号"""
    frame = inspect.currentframe()
    try:
        for _ in range(skip_frames):
            if frame is None:
                return "unknown:0"
            frame = frame.f_back

        if frame is None:
            return "unknown:0"

        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        return f"{filename}:{lineno}"
    finally:
        del frame


# ============ Structlog 处理器 ============
def add_context_info(logger, method_name, event_dict):
    """添加上下文信息到日志事件"""
    event_dict["request_id"] = get_request_id()
    tenant_id = get_tenant_id()
    if tenant_id:
        event_dict["tenant_id"] = tenant_id
    event_dict["app"] = get_app_type()
    return event_dict


def add_caller_location(logger, method_name, event_dict):
    """添加调用者位置信息到日志事件"""
    if "location" in event_dict:
        return event_dict

    frame = inspect.currentframe()
    try:
        skip_prefixes = (
            '/site-packages/',
            'lib/python',
            '/app/log/',
            '/logging/',
            '/structlog/',
        )

        while frame:
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno

            should_skip = any(p in filename for p in skip_prefixes)

            if not should_skip:
                event_dict["location"] = f"{filename}:{lineno}"
                return event_dict

            frame = frame.f_back

        return event_dict
    finally:
        del frame


# ============ 多应用 Logger 支持 ============
_internal_logger: Optional[structlog.BoundLogger] = None
_open_logger: Optional[structlog.BoundLogger] = None


def create_logger_for_app(app_type: str, log_file: str) -> structlog.BoundLogger:
    """为指定应用创建独立的 logger（只创建一次）"""
    app_logger = logging.getLogger(f"app.{app_type}")

    # 如果已经配置过，直接返回现有的 logger
    if hasattr(app_logger, "_configured") and app_logger._configured:
        return structlog.wrap_logger(
            app_logger,
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
        )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    app_logger.handlers = []
    app_logger.addHandler(file_handler)
    app_logger.addHandler(console_handler)
    app_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    app_logger.propagate = False
    app_logger._configured = True  # 标记已配置

    processors = [
        structlog.contextvars.merge_contextvars,
        add_context_info,
        add_caller_location,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(ensure_ascii=False),
    ]

    return structlog.wrap_logger(
        app_logger,
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
    )


def get_internal_logger() -> structlog.BoundLogger:
    """获取内部 API 的 logger"""
    global _internal_logger
    if _internal_logger is None:
        log_file = settings.LOG_FILE.replace(".log", "-internal.log")
        _internal_logger = create_logger_for_app("internal", log_file)
    return _internal_logger


def get_open_logger() -> structlog.BoundLogger:
    """获取 Open API 的 logger"""
    global _open_logger
    if _open_logger is None:
        log_file = settings.LOG_FILE.replace(".log", "-open.log")
        _open_logger = create_logger_for_app("open", log_file)
    return _open_logger


class LoggerProxy:
    """Logger 代理类 - 根据 ContextVar 自动选择 logger"""

    def _get_logger(self) -> structlog.BoundLogger:
        app_type = get_app_type()
        if app_type == "open":
            return get_open_logger()
        return get_internal_logger()

    def debug(self, *args, **kwargs):
        return self._get_logger().debug(*args, **kwargs)

    def info(self, *args, **kwargs):
        return self._get_logger().info(*args, **kwargs)

    def warning(self, *args, **kwargs):
        return self._get_logger().warning(*args, **kwargs)

    def warn(self, *args, **kwargs):
        return self._get_logger().warn(*args, **kwargs)

    def error(self, *args, **kwargs):
        return self._get_logger().error(*args, **kwargs)

    def exception(self, *args, **kwargs):
        return self._get_logger().exception(*args, **kwargs)

    def critical(self, *args, **kwargs):
        return self._get_logger().critical(*args, **kwargs)

    def fatal(self, *args, **kwargs):
        return self._get_logger().fatal(*args, **kwargs)

    def bind(self, **kwargs):
        return self._get_logger().bind(**kwargs)

    def unbind(self, *args):
        return self._get_logger().unbind(*args)

    def new(self, **kwargs):
        return self._get_logger().new(**kwargs)

    def try_unbind(self, *args):
        return self._get_logger().try_unbind(*args)


# 全局 logger 代理实例
logger = LoggerProxy()


# ============ 初始化函数 ============
def setup_logger():
    """初始化日志配置
    
    只创建两个日志文件：
    - app-internal.log: 内部 API 日志 (JWT 认证)
    - app-open.log: Open API 日志 (API Key 认证)
    
    不再创建 app.log
    """
    # 配置标准库 logging 基础处理器（控制台输出）
    handlers = []

    if settings.LOG_CONSOLE_OUTPUT:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        handlers.append(console_handler)

    # 注意：不再创建 app.log 文件
    # 日志会通过 LoggerProxy 自动分流到 app-internal.log 或 app-open.log

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        handlers=handlers,
        format="%(message)s",
        force=True,
    )

    # 禁用 uvicorn 日志
    for name in ["uvicorn.access", "uvicorn.error", "uvicorn"]:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = [logging.NullHandler()]
        uvicorn_logger.propagate = False
        uvicorn_logger.setLevel(logging.CRITICAL + 1)

    # 预创建 internal 和 open logger，确保它们不会 propagate 到 root logger
    # 同时创建文件 handler，确保日志文件存在
    get_internal_logger()
    get_open_logger()


__all__ = [
    "logger",
    "setup_logger",
    "set_request_id",
    "get_request_id",
    "set_tenant_id",
    "get_tenant_id",
    "set_app_type",
    "get_app_type",
    "get_exception_location",
    "get_caller_location",
    "is_request_logged",
    "set_request_logged",
]
