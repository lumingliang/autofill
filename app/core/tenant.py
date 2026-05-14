"""
租户上下文管理

提供统一的租户 ID 获取和数据隔离逻辑
"""
from typing import Optional, Any
from contextvars import ContextVar

from app.models import User

CTX_TENANT_ID: ContextVar[int] = ContextVar('tenant_id', default=0)
CTX_USER: ContextVar[Optional[User]] = ContextVar('user', default=None)


class TenantContext:
    """租户上下文管理器"""

    @classmethod
    def set_user(cls, user: User) -> None:
        """设置当前用户"""
        CTX_USER.set(user)

    @classmethod
    def get_user(cls) -> Optional[User]:
        """获取当前用户"""
        return CTX_USER.get()

    @classmethod
    def get_user_id(cls) -> int:
        """获取当前用户ID"""
        user = CTX_USER.get()
        return user.id if user else 0

    @classmethod
    def is_superuser(cls) -> bool:
        """检查是否为超级管理员"""
        user = CTX_USER.get()
        return getattr(user, 'is_superuser', False) if user else False

    @classmethod
    def get_tenant_id(cls, request_tenant_id: int = 0) -> int:
        """
        获取有效的租户ID

        规则:
        - 超级管理员：优先使用请求中传入的 tenant_id，否则返回 0（表示无限制）
        - 普通用户：使用用户自己的租户 ID

        Args:
            request_tenant_id: 请求中传入的租户ID（仅超级管理员有效）

        Returns:
            int: 有效的租户ID，0表示无限制
        """
        user = CTX_USER.get()

        if not user:
            return 0

        if cls.is_superuser():
            # 超级管理员：使用请求中传入的 tenant_id（如果有）
            return request_tenant_id if request_tenant_id > 0 else 0
        else:
            # 普通用户：使用自己的租户ID
            return getattr(user, 'current_tenant_id', 0)

    @classmethod
    def build_query_filter(cls, request_tenant_id: int = 0, tenant_field: str = 'tenant_id') -> dict:
        """
        构建租户查询过滤条件

        Args:
            request_tenant_id: 请求中传入的租户ID
            tenant_field: 租户字段名

        Returns:
            dict: 查询过滤条件
        """
        effective_tenant_id = cls.get_tenant_id(request_tenant_id)

        if effective_tenant_id > 0:
            return {tenant_field: effective_tenant_id}
        else:
            # 无租户限制或超级管理员，返回空条件
            return {}

    @classmethod
    def require_tenant(cls, request_tenant_id: int = 0) -> int:
        """
        要求有效的租户ID（不能为0）

        Args:
            request_tenant_id: 请求中传入的租户ID

        Returns:
            int: 有效的租户ID

        Raises:
            ValueError: 当没有有效租户时抛出
        """
        tenant_id = cls.get_tenant_id(request_tenant_id)

        if tenant_id <= 0:
            raise ValueError("缺少有效的租户ID")

        return tenant_id

    @classmethod
    def can_access_tenant(cls, target_tenant_id: int, request_tenant_id: int = 0) -> bool:
        """
        检查是否可以访问指定租户的数据

        Args:
            target_tenant_id: 目标租户ID
            request_tenant_id: 请求中传入的租户ID

        Returns:
            bool: 是否可以访问
        """
        effective_tenant_id = cls.get_tenant_id(request_tenant_id)

        if effective_tenant_id <= 0:
            # 超级管理员且未指定租户，可以访问任何租户
            return True

        return effective_tenant_id == target_tenant_id

    @classmethod
    def clear(cls) -> None:
        """清除上下文"""
        CTX_USER.set(None)
        CTX_TENANT_ID.set(0)
