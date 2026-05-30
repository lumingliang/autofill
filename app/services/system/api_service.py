"""
API Service 层

处理API相关的业务逻辑，包括：
- 获取用户API权限

约束：
- 使用 @atomic 装饰器控制事务
- 不重复判断权限（中间件已完成认证）
- 租户信息从 Ctx 获取
- 不直接查询 Model 层，通过 Repository 层访问数据
"""

from typing import List

from app.core.ctx import Ctx
from app.models.admin import Api
from app.repositories import api_repository


class ApiService:
    """
    API Service

    职责：
    - 处理API相关的业务逻辑
    - 调用 Repository 层进行数据操作

    约束：
    - 不直接操作数据库，通过 Repository 层访问数据
    - 不处理 HTTP 请求/响应
    """

    async def get_user_apis(self, user_id: int, is_superuser: bool) -> List[str]:
        """
        获取用户API权限

        Args:
            user_id: 用户ID
            is_superuser: 是否为超级管理员

        Returns:
            API路径列表 (method + path 格式)
        """
        if is_superuser:
            api_objs: List[Api] = await api_repository.get_all()
            return [api.method.lower() + api.path for api in api_objs]

        current_tenant_id = Ctx.get_effective_tenant_id()
        if not current_tenant_id:
            return []

        api_ids = await api_repository.get_user_api_ids(user_id)
        if not api_ids:
            return []

        api_objs = await api_repository.get_by_ids(list(api_ids))
        apis = list(set(api.method.lower() + api.path for api in api_objs))
        return apis


api_service = ApiService()
