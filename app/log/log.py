"""
统一日志模块 - FastAPI + Loguru + JSON 格式
"""
import json
import logging
import os
import sys
from contextvars import ContextVar

from loguru import logger

from app.settings import settings

# 请求追踪 ID 上下文变量
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
tenant_domain_var: ContextVar[str] = ContextVar("tenant_domain", default="")


def get_request_id() -> str:
    return request_id_var.get()


def set_request_id(request_id: str):
    request_id_var.set(request_id)


def get_tenant_domain() -> str:
    return tenant_domain_var.get()


def set_tenant_domain(tenant_domain: str):
    tenant_domain_var.set(tenant_domain)


def patch_record(record):
    """在序列化前修改记录，添加自定义字段"""
    exc = record.get("exception")

    # 获取异常发生的位置（最底层帧）
    exc_location = None
    if exc:
        tb = exc.traceback
        while tb:
            exc_location = f"{tb.tb_frame.f_code.co_filename}:{tb.tb_lineno}"
            tb = tb.tb_next

    # 构建 JSON 数据
    log_data = {
        "time": record["time"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "level": record["level"].name,
        "location": f"{record['file'].path}:{record['line']}" if hasattr(record['file'], 'path') else f"{record['name']}:{record['line']}",
        "message": record["message"],
    }

    # 添加异常信息
    if exc:
        log_data["error"] = {
            "type": exc.type.__name__,
            "message": str(exc.value),
            "location": exc_location
        }

    # 添加请求追踪信息
    req_id = get_request_id()
    if req_id:
        log_data["request_id"] = req_id

    tenant_domain = get_tenant_domain()
    if tenant_domain:
        log_data["tenant_domain"] = tenant_domain

    # 添加 extra 中绑定的其他字段（如 request_params, response 等）
    # 排除内部使用的 _json 字段
    extra_data = {k: v for k, v in record["extra"].items() if not k.startswith("_")}
    if extra_data:
        log_data.update(extra_data)

    # 存储序列化后的 JSON
    record["extra"]["_json"] = json.dumps(log_data, ensure_ascii=False, default=str)

    # 清除异常信息，防止 loguru 输出 traceback 到控制台
    if record.get("exception"):
        record["exception"] = None


# 应用 patch
logger = logger.patch(patch_record)


# 拦截 uvicorn 原生日志
class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        
        # 自动回溯真实调用代码行
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logger():
    """初始化日志配置"""
    # 清空 loguru 默认处理器
    logger.remove()

    # JSON 格式模板
    json_format = "{extra[_json]}\n"
    
    # 1. 控制台 JSON 输出
    if settings.LOG_CONSOLE_OUTPUT:
        logger.add(
            sys.stdout,
            level=settings.LOG_LEVEL,
            format=json_format,
            enqueue=True,
            backtrace=False,
            diagnose=False,
        )
    
    # 2. 文件 JSON 日志
    if settings.LOG_FILE_OUTPUT:
        log_dir = os.path.dirname(settings.LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        logger.add(
            settings.LOG_FILE,
            level=settings.LOG_LEVEL,
            format=json_format,
            rotation=settings.LOG_MAX_BYTES * 1024 * 1024,
            retention=settings.LOG_BACKUP_COUNT,
            encoding="utf-8",
            enqueue=True,
            compression="gz",
            backtrace=False,
            diagnose=False,
        )
    
    # 全局接管 uvicorn/fastapi 日志（排除 uvicorn.access，由 RequestLoggingMiddleware 处理）
    logging.basicConfig(
        handlers=[InterceptHandler()],
        level=logging.INFO,
        force=True
    )

    # 清除 uvicorn 原有 handler，防止重复输出
    for log_name in ["uvicorn", "uvicorn.error", "fastapi"]:
        _logger = logging.getLogger(log_name)
        _logger.handlers.clear()
        _logger.propagate = True

    # 禁用 uvicorn.access 日志，避免与 RequestLoggingMiddleware 重复
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers.clear()
    uvicorn_access.addHandler(logging.NullHandler())
    uvicorn_access.propagate = False
    
    return logger


__all__ = ["logger", "setup_logger", "set_request_id", "get_request_id", "set_tenant_domain", "get_tenant_domain"]
