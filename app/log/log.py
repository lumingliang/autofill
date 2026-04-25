import json
import os
import sys
from contextvars import ContextVar
from typing import Any, Dict

from loguru import logger as loguru_logger

# 请求追踪 ID 上下文变量
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
tenant_domain_var: ContextVar[str] = ContextVar("tenant_domain", default="")

# 全局变量，用于延迟初始化
_logger = None


def get_request_id() -> str:
    """获取当前请求的追踪 ID"""
    return request_id_var.get()


def set_request_id(request_id: str):
    """设置当前请求的追踪 ID"""
    request_id_var.set(request_id)


def get_tenant_domain() -> str:
    """获取当前租户域名"""
    return tenant_domain_var.get()


def set_tenant_domain(tenant_domain: str):
    """设置当前租户域名"""
    tenant_domain_var.set(tenant_domain)


def patching(record: Dict[str, Any]) -> None:
    """在日志记录被序列化前修改它，添加自定义字段"""
    # 添加请求追踪 ID
    req_id = get_request_id()
    if req_id:
        record["extra"]["request_id"] = req_id

    # 添加租户域名
    tenant_domain = get_tenant_domain()
    if tenant_domain:
        record["extra"]["tenant_domain"] = tenant_domain

    # 构建完整的 extra 数据用于 JSON 输出
    extra_data = dict(record["extra"])

    # 创建序列化后的 JSON 字符串存储在 extra 中
    log_data: Dict[str, Any] = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "logger": record["name"],
        "file": record["file"].path,
        "line": record["line"],
        "function": record["function"],
        "thread": record["thread"].id,
        "process": record["process"].id,
    }

    # 添加请求追踪 ID 到主数据
    if req_id:
        log_data["request_id"] = req_id

    # 添加租户域名到主数据
    if tenant_domain:
        log_data["tenant_domain"] = tenant_domain

    # 添加额外的上下文信息
    if extra_data:
        for key, value in extra_data.items():
            if key not in log_data and key not in ("request_id", "tenant_domain", "_json_output"):
                log_data[key] = value

    # 添加异常信息
    if record["exception"] is not None:
        exception_data = record["exception"]
        log_data["exception"] = {
            "type": exception_data.type.__name__ if exception_data.type else None,
            "value": str(exception_data.value) if exception_data.value else None,
            "traceback": exception_data.traceback,
        }

    # 将序列化后的 JSON 存储在 extra 中，供 formatter 使用
    record["extra"]["_json_output"] = json.dumps(log_data, ensure_ascii=False, default=str)


class Loggin:
    def __init__(self) -> None:
        # 延迟导入 settings，确保配置已加载
        from app.settings import settings

        # 从配置读取日志设置
        self.level = settings.LOG_LEVEL
        self.log_file = settings.LOG_FILE
        self.max_bytes = settings.LOG_MAX_BYTES * 1024 * 1024  # 转换为字节
        self.backup_count = settings.LOG_BACKUP_COUNT
        self.console_output = settings.LOG_CONSOLE_OUTPUT
        self.file_output = settings.LOG_FILE_OUTPUT

    def setup_logger(self):
        _logger = loguru_logger
        _logger.remove()

        # 应用 patch 来修改记录
        _logger = _logger.patch(patching)

        # JSON 格式字符串，使用 extra 中存储的序列化 JSON
        json_formatter = "{extra[_json_output]}\n"

        # 控制台输出 - JSON 格式
        if self.console_output:
            _logger.add(
                sink=sys.stdout,
                level=self.level,
                format=json_formatter,
            )

        # 文件输出 - JSON 格式，支持轮转
        if self.file_output:
            log_dir = os.path.dirname(self.log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            _logger.add(
                sink=self.log_file,
                level=self.level,
                format=json_formatter,
                rotation=self.max_bytes,
                retention=self.backup_count,
                encoding="utf-8",
                enqueue=True,
                compression="gz",  # 压缩旧日志文件
            )

        return _logger


def get_logger():
    """延迟初始化 logger"""
    global _logger
    if _logger is None:
        loggin = Loggin()
        _logger = loggin.setup_logger()
    return _logger


# 为了保持兼容性，使用代理对象
class LoggerProxy:
    """logger 代理类，延迟初始化实际的 logger"""

    def __init__(self):
        self._logger = None

    def _get_logger(self):
        if self._logger is None:
            self._logger = get_logger()
        return self._logger

    def __getattr__(self, name):
        return getattr(self._get_logger(), name)

    def __call__(self, *args, **kwargs):
        return self._get_logger()(*args, **kwargs)

    # 直接代理常用日志方法，确保它们能被正确调用
    def debug(self, msg, *args, **kwargs):
        return self._get_logger().debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        return self._get_logger().info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        return self._get_logger().warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        return self._get_logger().error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        return self._get_logger().critical(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        return self._get_logger().exception(msg, *args, **kwargs)

    # 添加上下文日志方法
    def bind(self, **kwargs):
        """绑定上下文信息到日志"""
        return self._get_logger().bind(**kwargs)

    def context(self, **kwargs):
        """创建带上下文的日志记录器"""
        return self._get_logger().bind(**kwargs)


logger = LoggerProxy()
