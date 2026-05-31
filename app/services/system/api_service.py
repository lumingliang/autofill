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

from typing import List, Tuple

from fastapi.routing import APIRoute

from app.core.ctx import Ctx
from app.log import logger
from app.models.admin import Api
from app.repositories import api_repository
from app.settings import settings
from tortoise.expressions import Q


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

    async def get_user_apis(self) -> List[str]:
        """
        获取当前用户API权限

        Returns:
            API路径列表 (method + path 格式)
        """
        if Ctx.is_superuser():
            api_objs: List[Api] = await api_repository.get_all()
            return [api.method.lower() + api.path for api in api_objs]

        current_tenant_id = Ctx.get_effective_tenant_id()
        if not current_tenant_id:
            return []

        user = Ctx.get_user()
        api_ids = await api_repository.get_user_api_ids(user.id)
        if not api_ids:
            return []

        api_objs = await api_repository.get_by_ids(list(api_ids))
        apis = list(set(api.method.lower() + api.path for api in api_objs))
        return apis

    async def list(
        self,
        path: str = "",
        summary: str = "",
        tags: str = "",
        api_code: str = "",
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[int, List[Api]]:
        """
        分页获取API列表

        Args:
            path: API路径关键字
            summary: API简介关键字
            tags: API标签关键字
            api_code: API编码关键字
            page: 页码
            page_size: 每页数量

        Returns:
            Tuple[int, List[Api]]: (总数, API列表)
        """
        q = Q()
        if path:
            q &= Q(path__contains=path)
        if summary:
            q &= Q(summary__contains=summary)
        if tags:
            q &= Q(tags__contains=tags)
        if api_code:
            q &= Q(api_code__contains=api_code)

        return await api_repository.list(
            page=page,
            page_size=page_size,
            search=q,
            order=["-updated_at"]
        )

    async def list_with_permission(
        self,
        path: str = "",
        summary: str = "",
        tags: str = "",
        api_code: str = "",
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[int, List[Api]]:
        """
        根据用户权限获取API列表

        Args:
            path: API路径关键字
            summary: API简介关键字
            tags: API标签关键字
            api_code: API编码关键字
            page: 页码
            page_size: 每页数量

        Returns:
            Tuple[int, List[Api]]: (总数, API列表)
        """
        q = Q()
        if path:
            q &= Q(path__contains=path)
        if summary:
            q &= Q(summary__contains=summary)
        if tags:
            q &= Q(tags__contains=tags)
        if api_code:
            q &= Q(api_code__contains=api_code)

        if Ctx.is_superuser():
            return await api_repository.list(
                page=page,
                page_size=page_size,
                search=q,
                order=["-updated_at"]
            )

        current_tenant_id = Ctx.get_effective_tenant_id()
        if not current_tenant_id:
            return 0, []

        user = Ctx.get_user()
        allowed_api_ids = await api_repository.get_user_api_ids_by_tenant(user.id, current_tenant_id)

        if not allowed_api_ids:
            return 0, []

        q &= Q(id__in=list(allowed_api_ids))
        return await api_repository.list(
            page=page,
            page_size=page_size,
            search=q,
            order=["-updated_at"]
        )

    def _should_manage_api(self, route: APIRoute) -> bool:
        """
        判断是否应该将该路由纳入 API 管理
        - 排除包含特定 tags 的 API（可配置，如公开接口、文件上传等）
        - 只管理需要权限控制的后台 API
        """
        if not isinstance(route, APIRoute):
            return False
        if len(route.dependencies) == 0:
            return False

        # 使用 tags 进行排除过滤（可配置）
        route_tags = set(route.tags) if route.tags else set()
        exclude_tags = set(settings.EXCLUDE_API_TAGS)

        # 如果路由的 tags 与排除列表有交集，则不纳入管理
        if route_tags & exclude_tags:
            return False

        return True

    def generate_api_code(self, path: str, method: str) -> str:
        """
        生成API Code - 纯算法确保全局唯一性，无需查询数据库
        规则: {resource}:{action}:{method}
        """
        path = path.replace("/api/v1/", "").strip("/")
        parts = path.split("/")

        if len(parts) >= 2:
            resource = parts[0]
            action_parts = []
            for p in parts[1:]:
                p = p.replace("{", "").replace("}", "")
                action_parts.append(p)
            action = "_".join(action_parts)
        elif len(parts) == 1:
            resource = parts[0]
            action = "default"
        else:
            resource = "unknown"
            action = "default"

        method_lower = method.lower()
        return f"{resource}:{action}:{method_lower}"

    async def refresh_api(self, app):
        """
        刷新API列表

        从 FastAPI app 的路由中提取 API 信息并存储到数据库
        """
        all_api_list = []
        for route in app.routes:
            if self._should_manage_api(route):
                all_api_list.append((list(route.methods)[0], route.path_format))

        db_api_list = await api_repository.get_all_method_path_pairs()

        delete_api_ids = []
        for api in db_api_list:
            if api not in all_api_list:
                api_obj = await api_repository.get_by_method_path(api[0], api[1])
                if api_obj:
                    delete_api_ids.append(api_obj.id)

        if delete_api_ids:
            await api_repository.delete_by_ids(delete_api_ids)
            for api_id in delete_api_ids:
                logger.debug(f"API Deleted id={api_id}")

        for route in app.routes:
            if self._should_manage_api(route):
                method = list(route.methods)[0]
                path = route.path_format
                summary = route.summary
                tags = list(route.tags)[0] if route.tags else ""

                api_code = self.generate_api_code(path, method)

                api_obj = await api_repository.get_by_method_path(method, path)
                if api_obj:
                    await api_repository.update(api_obj.id, dict(
                        api_code=api_code,
                        method=method,
                        path=path,
                        summary=summary,
                        tags=tags
                    ))
                else:
                    logger.debug(f"API Created {api_code} {method} {path}")
                    await api_repository.create(dict(
                        api_code=api_code,
                        method=method,
                        path=path,
                        summary=summary,
                        tags=tags
                    ))


api_service = ApiService()
