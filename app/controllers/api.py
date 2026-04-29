from fastapi.routing import APIRoute

from app.core.crud import CRUDBase
from app.log import logger
from app.models.admin import Api
from app.schemas.apis import ApiCreate, ApiUpdate


class ApiController(CRUDBase[Api, ApiCreate, ApiUpdate]):
    def __init__(self):
        super().__init__(model=Api)

    def _should_manage_api(self, route: APIRoute) -> bool:
        """
        判断是否应该将该路由纳入 API 管理
        - 只管理后台 CURD API (以 /api/v1 开头)
        - 排除公开 API (Dify/三方调用，使用 API Key 认证)
        """
        if not isinstance(route, APIRoute):
            return False
        if len(route.dependencies) == 0:
            return False
        # 只管理 /api/v1 开头的 API (后台管理接口)
        # 排除 /api/autofill/ 开头的公开接口 (智能填单公开接口)
        # 排除 /api/llm/ 开头的公开接口 (LLM代理公开接口)
        path = route.path_format
        if path.startswith("/api/autofill/"):
            return False
        if path.startswith("/api/llm/"):
            return False
        if not path.startswith("/api/v1/"):
            return False
        return True

    async def refresh_api(self):
        from app import app

        # 删除废弃API数据
        all_api_list = []
        for route in app.routes:
            if self._should_manage_api(route):
                all_api_list.append((list(route.methods)[0], route.path_format))
        delete_api = []
        for api in await Api.all():
            if (api.method, api.path) not in all_api_list:
                delete_api.append((api.method, api.path))
        for item in delete_api:
            method, path = item
            logger.debug(f"API Deleted {method} {path}")
            await Api.filter(method=method, path=path).delete()

        for route in app.routes:
            if self._should_manage_api(route):
                method = list(route.methods)[0]
                path = route.path_format
                summary = route.summary
                tags = list(route.tags)[0] if route.tags else ""
                api_obj = await Api.filter(method=method, path=path).first()
                if api_obj:
                    await api_obj.update_from_dict(dict(method=method, path=path, summary=summary, tags=tags)).save()
                else:
                    logger.debug(f"API Created {method} {path}")
                    await Api.create(**dict(method=method, path=path, summary=summary, tags=tags))


api_controller = ApiController()
