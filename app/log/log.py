"""
统一日志模块 - 基于 structlog 的结构化日志
主要字段：request_id, tenant_id, elapsed_time, exception(filename:lineno)
"""
import inspect
import logging
import sys
from contextvars import ContextVar
from datetime import datetime
from zoneinfo import ZoneInfo

import structlog

from app.settings import settings


def get_local_timestamp() -> str:
    """获取本地时区时间戳"""
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()

# 请求追踪 ID 上下文变量
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
tenant_id_var: ContextVar[int] = ContextVar("tenant_id", default=0)
# 标记请求日志是否已被记录
request_logged_var: ContextVar[bool] = ContextVar("request_logged", default=False)


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


def get_exception_location(exc_info):
    """获取异常发生的位置（业务代码中的位置）
    
    遍历 traceback 链，找到最底层的业务代码帧（即异常实际抛出的位置）
    排除第三方库和框架内部的帧
    """
    if not exc_info or exc_info[2] is None:
        return None
    
    tb = exc_info[2]
    last_business_frame = None
    
    # 遍历整个 traceback 链，找到最底层的业务代码帧
    while tb:
        filename = tb.tb_frame.f_code.co_filename
        lineno = tb.tb_lineno
        
        # 排除第三方库和框架内部代码
        if '/site-packages/' in filename or 'lib/python' in filename:
            tb = tb.tb_next
            continue
        
        # 记录业务代码帧（继续遍历以找到最底层的）
        last_business_frame = (filename, lineno)
        tb = tb.tb_next
    
    # 返回最底层的业务代码位置
    if last_business_frame:
        return f"{last_business_frame[0]}:{last_business_frame[1]}"
    
    # 如果没有找到业务代码位置，返回最底层帧
    tb = exc_info[2]
    while tb.tb_next:
        tb = tb.tb_next
    return f"{tb.tb_frame.f_code.co_filename}:{tb.tb_lineno}"


def get_caller_location(skip_frames: int = 2) -> str:
    """获取调用者的文件位置和行号

    Args:
        skip_frames: 跳过的帧数，默认为2（跳过当前函数和调用者）

    Returns:
        str: 文件路径:行号
    """
    frame = inspect.currentframe()
    try:
        # 跳过指定帧数
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


def add_context_info(logger, method_name, event_dict):
    """添加上下文信息到日志事件"""
    event_dict["request_id"] = get_request_id()
    tenant_id = get_tenant_id()
    if tenant_id:
        event_dict["tenant_id"] = tenant_id
    return event_dict


def add_caller_location(logger, method_name, event_dict):
    """添加调用者位置信息到日志事件
    
    通过检查调用栈，找到实际调用日志记录的业务代码位置
    """
    frame = inspect.currentframe()
    try:
        # 向上遍历调用栈，跳过框架和日志相关的帧
        # 需要跳过的模块前缀
        skip_prefixes = (
            '/site-packages/',
            'lib/python',
            '/app/log/',
            '/logging/',
            '/structlog/',
        )
        
        # 从当前帧开始向上遍历
        while frame:
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno
            
            # 检查是否需要跳过
            should_skip = any(p in filename for p in skip_prefixes)
            
            if not should_skip:
                # 找到业务代码帧
                event_dict["location"] = f"{filename}:{lineno}"
                return event_dict
            
            frame = frame.f_back
        
        # 如果没有找到业务代码帧，不添加位置信息
        return event_dict
    finally:
        del frame


def setup_logger():
    """初始化 structlog 配置"""
    # 配置标准库 logging 处理器
    handlers = []
    
    if settings.LOG_CONSOLE_OUTPUT:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        handlers.append(console_handler)
    
    if settings.LOG_FILE_OUTPUT:
        file_handler = logging.FileHandler(settings.LOG_FILE, encoding="utf-8")
        file_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        handlers.append(file_handler)
    
    # 配置根日志器
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        handlers=handlers,
        format="%(message)s",
        force=True,
    )
    
    # 配置 structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            add_context_info,
            add_caller_location,  # 添加调用者位置信息
            structlog.processors.TimeStamper(fmt="iso", utc=False),
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # 抑制 uvicorn 和 fastapi 的访问日志（由 RequestLoggingMiddleware 统一处理）
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False
    
    # 抑制 uvicorn.error 的默认异常输出（避免控制台打印完整 traceback）
    # 异常已由我们的全局异常处理器记录到日志文件
    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.handlers = []
    uvicorn_error.propagate = False


# 获取 logger 实例
logger = structlog.get_logger()


__all__ = [
    "logger",
    "setup_logger",
    "set_request_id",
    "get_request_id",
    "set_tenant_id",
    "get_tenant_id",
    "get_exception_location",
    "get_caller_location",
]
