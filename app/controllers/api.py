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

    def generate_api_code(self, path: str, method: str) -> str:
        """
        生成API Code - 纯算法确保全局唯一性，无需查询数据库
        规则: {resource}:{action}:{method}
        
        示例:
          - GET /api/v1/user/list -> user:list:get
          - POST /api/v1/user/create -> user:create:post
          - GET /api/v1/autofill/app -> autofill:app:get
          - POST /api/v1/autofill/app -> autofill:app:post
          - GET /api/v1/user/role/list -> user:role_list:get
          - PUT /api/v1/user/update/1 -> user:update_id:put
        """
        # 移除 /api/v1/ 前缀
        path = path.replace("/api/v1/", "").strip("/")
        parts = path.split("/")

        if len(parts) >= 2:
            resource = parts[0]
            # 将剩余路径部分用下划线连接作为action
            action_parts = []
            for p in parts[1:]:
                # 移除路径参数标记 {id} -> id
                p = p.replace("{", "").replace("}", "")
                action_parts.append(p)
            action = "_".join(action_parts)
        elif len(parts) == 1:
            resource = parts[0]
            action = "default"
        else:
            resource = "unknown"
            action = "default"

        # 方法名统一小写
        method_lower = method.lower()

        # 格式: resource:action:method，确保唯一性
        # 因为同一个path+method组合是唯一的，所以生成的api_code也是唯一的
        return f"{resource}:{action}:{method_lower}"

    async def refresh_api(self, app):
        # 删除废弃API数据
        all_api_list = []
        for route in app.routes:
            if self._should_manage_api(route):
                all_api_list.append((list(route.methods)[0], route.path_format))
        delete_api = []
        for api in await Api.all():
            if (api.method, api.path) not in all_api_list:
                delete_api.append(api.id)
        for api_id in delete_api:
            logger.debug(f"API Deleted id={api_id}")
            await Api.filter(id=api_id).delete()

        for route in app.routes:
            if self._should_manage_api(route):
                method = list(route.methods)[0]
                path = route.path_format
                summary = route.summary
                tags = list(route.tags)[0] if route.tags else ""
                
                # 直接生成唯一的api_code，无需查询数据库
                # 因为path+method组合是唯一的，所以生成的api_code也是唯一的
                api_code = self.generate_api_code(path, method)

                api_obj = await Api.filter(method=method, path=path).first()
                if api_obj:
                    await api_obj.update_from_dict(dict(
                        api_code=api_code,
                        method=method,
                        path=path,
                        summary=summary,
                        tags=tags
                    ))
                else:
                    logger.debug(f"API Created {api_code} {method} {path}")
                    await Api.create(**dict(
                        api_code=api_code,
                        method=method,
                        path=path,
                        summary=summary,
                        tags=tags
                    ))


api_controller = ApiController()
