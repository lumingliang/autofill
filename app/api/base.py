"""
API 层基础类

提供通用的 API 层校验和工具方法
"""

from fastapi import HTTPException

from app.core.ctx import Ctx


class BaseAPI:
    """
    API 层基础类

    职责：
    - 提供通用的参数校验方法
    - 提供通用的权限检查方法
    - 封装常用的 API 层逻辑

    约束：
    - 不涉及业务逻辑，只处理参数校验
    - 不直接操作数据库
    """

    @staticmethod
    def require_tenant_id() -> int:
        """
        获取并验证当前租户ID

        从 Ctx 获取 effective_tenant_id（超管使用 request_tenant_id，普通用户使用 jwt_tenant_id）
        如果 tenant_id <= 0，抛出 HTTPException

        Returns:
            int: 当前租户ID

        Raises:
            HTTPException: 如果未指定租户ID
        """
        tenant_id = Ctx.get_effective_tenant_id()
        if tenant_id <= 0:
            raise HTTPException(status_code=400, detail="请指定租户ID")
        return tenant_id

    @staticmethod
    def get_current_user_id() -> int:
        """
        获取当前用户ID

        Returns:
            int: 当前用户ID

        Raises:
            HTTPException: 如果未认证
        """
        user = Ctx.get_user()
        if not user:
            raise HTTPException(status_code=401, detail="未认证")
        return user.id

    @staticmethod
    def require_superuser():
        """
        要求当前用户是超级管理员

        Raises:
            HTTPException: 如果不是超级管理员
        """
        user = Ctx.get_user()
        if not user:
            raise HTTPException(status_code=401, detail="未认证")
        if not user.is_superuser:
            raise HTTPException(status_code=403, detail="需要超级管理员权限")

    @staticmethod
    def get_current_tenant_id_or_none() -> int:
        """
        获取当前租户ID，如果不存在返回 0

        Returns:
            int: 当前租户ID，如果没有则返回 0
        """
        return Ctx.get_effective_tenant_id()
