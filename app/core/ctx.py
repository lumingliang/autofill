"""
全局请求上下文管理模块

提供统一的请求上下文管理，包括：
- 当前用户信息
- JWT Token 中的租户ID
- 请求参数中的租户ID（仅超管有效）
- 后台任务
"""

import contextvars
from typing import Any, Dict, Optional

from starlette.background import BackgroundTasks

from app.models.admin import User

# 上下文变量定义
CTX_USER_ID: contextvars.ContextVar[int] = contextvars.ContextVar("user_id", default=0)
CTX_BG_TASKS: contextvars.ContextVar[BackgroundTasks] = contextvars.ContextVar("bg_task", default=None)
CTX_USER: contextvars.ContextVar[Optional[User]] = contextvars.ContextVar("user", default=None)
CTX_JWT_TENANT_ID: contextvars.ContextVar[int] = contextvars.ContextVar("jwt_tenant_id", default=0)
CTX_REQUEST_TENANT_ID: contextvars.ContextVar[int] = contextvars.ContextVar("request_tenant_id", default=0)


class Ctx:
    """
    请求上下文管理类

    提供统一的方法来管理请求生命周期内的上下文信息：
    - 用户信息（User）
    - JWT Token 中的租户ID（jwt_tenant_id）
    - 请求参数中的租户ID（request_tenant_id，仅超管有效）

    使用方式：
    - 在中间件中设置上下文
    - 在 Repository/Service 层获取上下文
    - 请求结束后自动清理
    """

    @classmethod
    def set_user(cls, user: User) -> None:
        """设置当前用户"""
        CTX_USER.set(user)
        if user:
            CTX_USER_ID.set(user.id)

    @classmethod
    def get_user(cls) -> Optional[User]:
        """获取当前用户"""
        return CTX_USER.get()

    @classmethod
    def set_jwt_tenant_id(cls, tenant_id: int) -> None:
        """设置JWT Token中解析的租户ID"""
        CTX_JWT_TENANT_ID.set(tenant_id)

    @classmethod
    def get_jwt_tenant_id(cls) -> int:
        """获取JWT Token中解析的租户ID"""
        return CTX_JWT_TENANT_ID.get()

    @classmethod
    def set_request_tenant_id(cls, tenant_id: int) -> None:
        """设置请求参数中的租户ID（仅超管有效）"""
        CTX_REQUEST_TENANT_ID.set(tenant_id)

    @classmethod
    def get_request_tenant_id(cls) -> int:
        """获取请求参数中的租户ID"""
        return CTX_REQUEST_TENANT_ID.get()

    @classmethod
    def get_effective_tenant_id(cls) -> int:
        """
        获取有效的租户ID

        逻辑：
        - 普通用户：强制使用JWT中的租户ID
        - 超管：如果请求参数中指定了租户ID，则使用；否则返回0（不过滤）

        Returns:
            int: 有效的租户ID，0表示不过滤
        """
        user = cls.get_user()
        if not user:
            return 0

        if user.is_superuser:
            # 超管：使用请求参数中的租户ID，未指定则返回0（不过滤）
            request_tenant_id = cls.get_request_tenant_id()
            return request_tenant_id if request_tenant_id > 0 else 0
        else:
            # 普通用户：强制使用JWT中的租户ID
            return cls.get_jwt_tenant_id()

    @classmethod
    def build_query_filter(cls, tenant_field: str = "tenant_id") -> Dict[str, Any]:
        """
        构建租户查询过滤条件

        Args:
            tenant_field: 租户ID字段名，默认为"tenant_id"

        Returns:
            Dict: 过滤条件字典，空字典表示不过滤
        """
        effective_tenant_id = cls.get_effective_tenant_id()
        if effective_tenant_id > 0:
            return {tenant_field: effective_tenant_id}
        return {}

    @classmethod
    def is_superuser(cls) -> bool:
        """检查当前用户是否为超级管理员"""
        user = cls.get_user()
        return user.is_superuser if user else False

    @classmethod
    def should_query_all(cls) -> bool:
        """
        判断是否应查询全量数据（不过滤租户）

        适用场景：
        - 超管未指定租户ID时，需要查询所有租户的数据
        - 普通用户始终返回 False（需要按租户过滤）

        Returns:
            bool: True 表示查询全量数据，False 表示按租户过滤
        """
        return cls.get_effective_tenant_id() <= 0

    @classmethod
    def clear(cls) -> None:
        """清理所有上下文（请求结束时调用）"""
        CTX_USER.set(None)
        CTX_USER_ID.set(0)
        CTX_JWT_TENANT_ID.set(0)
        CTX_REQUEST_TENANT_ID.set(0)

    @classmethod
    def set_bg_tasks(cls, bg_tasks: BackgroundTasks) -> None:
        """设置后台任务"""
        CTX_BG_TASKS.set(bg_tasks)

    @classmethod
    def get_bg_tasks(cls) -> Optional[BackgroundTasks]:
        """获取后台任务"""
        return CTX_BG_TASKS.get()
