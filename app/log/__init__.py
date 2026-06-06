"""
统一日志模块

支持多应用日志自动分流：
- 内部 API (/api/v1/*) 日志写入 app-internal.log
- Open API (/api/v1/open/*) 日志写入 app-open.log

使用方式保持不变：
    from app.log import logger
    logger.info("message")

日志会根据当前请求路径自动分流到不同文件
"""
from .log import (
    logger,
    setup_logger,
    set_request_id,
    get_request_id,
    set_tenant_id,
    get_tenant_id,
    set_app_type,
    get_app_type,
    get_exception_location,
    get_caller_location,
    is_request_logged,
    set_request_logged,
)

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
