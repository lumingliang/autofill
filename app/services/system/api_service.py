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
from tortoise.expressions import Q

from app.core.bgtask import BgTasks
from app.core.ctx import Ctx
from app.log import logger
from app.models.admin import Api
from app.repositories import api_repository, role_api_repository
from app.settings import settings


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
        优化：一次性查询所有API到内存，减少数据库查询次数
        """
        # 1. 收集所有路由API信息
        route_apis = []
        for route in app.routes:
            if self._should_manage_api(route):
                method = list(route.methods)[0]
                path = route.path_format
                summary = route.summary
                tags = list(route.tags)[0] if route.tags else ""
                api_code = self.generate_api_code(path, method)
                route_apis.append({
                    "method": method,
                    "path": path,
                    "summary": summary,
                    "tags": tags,
                    "api_code": api_code,
                })

        # 2. 一次性查询所有数据库中的API
        all_db_apis = await api_repository.get_all()

        # 3. 构建内存索引：{(method, path): api_obj}
        db_api_map = {}
        for api in all_db_apis:
            key = (api.method, api.path)
            db_api_map[key] = api

        # 4. 构建路由API的key集合
        route_api_keys = {(api["method"], api["path"]) for api in route_apis}

        # 5. 找出需要删除的API（在数据库中但不在路由中）
        delete_api_ids = []
        for key, api_obj in db_api_map.items():
            if key not in route_api_keys:
                delete_api_ids.append(api_obj.id)

        if delete_api_ids:
            # 先删除角色-API关联（后台任务）
            await BgTasks.add_task(self._cleanup_role_api_relations, delete_api_ids)
            # 再删除API
            await api_repository.delete_by_ids(delete_api_ids)
            for api_id in delete_api_ids:
                logger.debug(f"API Deleted id={api_id}")

    async def _cleanup_role_api_relations(self, api_ids: List[int]) -> None:
        """
        后台任务：清理与已删除API关联的角色权限数据

        Args:
            api_ids: 已删除的API ID列表
        """
        try:
            deleted_count = await role_api_repository.delete_by_api_ids(api_ids)
            logger.info(f"[ApiService] 清理角色-API关联完成，删除 {deleted_count} 条记录，涉及API: {api_ids}")
        except Exception as e:
            logger.error(f"[ApiService] 清理角色-API关联失败: {e}, API IDs: {api_ids}")

        # 6. 批量更新和创建
        to_update = []
        to_create = []

        for route_api in route_apis:
            key = (route_api["method"], route_api["path"])
            db_api = db_api_map.get(key)

            if db_api:
                # 需要更新
                to_update.append({
                    "id": db_api.id,
                    "api_code": route_api["api_code"],
                    "method": route_api["method"],
                    "path": route_api["path"],
                    "summary": route_api["summary"],
                    "tags": route_api["tags"],
                })
            else:
                # 需要创建
                to_create.append(route_api)
                logger.debug(f"API Created {route_api['api_code']} {route_api['method']} {route_api['path']}")

        # 7. 执行批量操作
        if to_update:
            await api_repository.bulk_update(to_update)

        if to_create:
            await api_repository.bulk_create(to_create)


api_service = ApiService()
