import json
import sys
import traceback
import uuid
from datetime import datetime
from typing import Any

from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send, Message

from app.core.ctx import Ctx
from app.core.dependency import AuthControl
from app.core.relation import RelationQuery
from app.log import logger, set_request_id, set_tenant_id, get_caller_location, is_request_logged, set_request_logged
from app.models.admin import AuditLog, User
from app.settings import settings

from .bgtask import BgTasks

# Open API 前缀 - 这些接口使用 API Key 认证，不走 JWT 中间件
OPEN_API_PREFIX: str = "/api/v1/open/"


class SimpleBaseMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)

        response = await self.before_request(request) or self.app
        await response(request.scope, request.receive, send)
        await self.after_request(request)

    async def before_request(self, request: Request):
        return self.app

    async def after_request(self, request: Request):
        return None


class BackGroundTaskMiddleware(SimpleBaseMiddleware):
    async def before_request(self, request):
        await BgTasks.init_bg_tasks_obj()

    async def after_request(self, request):
        await BgTasks.execute_tasks()


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """
    异常捕获中间件 - 仅捕获异常，不记录日志

    功能：
    1. 捕获所有未处理的异常
    2. 重新抛出异常给全局异常处理器处理

    注意：
    - 异常日志由全局异常处理器统一记录
    - 此中间件仅确保异常能被正确捕获和传递
    """

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 异常由全局异常处理器捕获和记录
        return await call_next(request)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """请求追踪 ID 中间件"""

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        set_request_id(request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    租户上下文中间件 - 统一处理接口鉴权和租户验证

    接口分类：
    1. Open 接口 (/api/v1/open/*): 只走 autofill_auth，中间件不处理
    2. 后台接口无需鉴权: 不需要 is_authed 验证
    3. 后台接口需鉴权: is_authed + 租户归属验证

    权限分类：
    - base 接口: 不需要 has_permission
    - 其他接口: 需要 has_permission
    """

    def __init__(self, app):
        super().__init__(app)

        # 加载配置
        self.no_auth_paths = settings.NO_AUTH_PATHS or ["/api/v1/base/access_token"]
        self.base_prefixes = settings.BASE_API_PREFIXES or ["/api/v1/base/"]

    def _is_open_api(self, path: str) -> bool:
        """检查是否是 Open 接口（路径以 /api/v1/open/ 开头）"""
        return path.startswith(OPEN_API_PREFIX)

    def _is_no_auth_path(self, path: str) -> bool:
        """检查是否是无需鉴权的路径"""
        # 精确匹配
        if path in self.no_auth_paths:
            return True
        # 前缀匹配（支持 /static/* 等）
        for no_auth_path in self.no_auth_paths:
            if path.startswith(no_auth_path):
                return True
        return False

    def _is_base_api(self, path: str) -> bool:
        """检查是否是 base 接口（不需要 has_permission）"""
        return any(path.startswith(prefix) for prefix in self.base_prefixes)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # 2. Open 接口直接放行（由 autofill_auth 处理）
        if self._is_open_api(path):
            return await call_next(request)

        # 3. 无需鉴权的路径直接放行
        if self._is_no_auth_path(path):
            return await call_next(request)

        # 4. 需要鉴权的接口
        token = request.headers.get("token")
        if not token:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "msg": "缺少认证token", "data": None}
            )

        try:
            # 4.1 认证用户
            user = await AuthControl.is_authed(token)

            # 4.2 获取请求中的租户ID
            request_tenant_id = await self._get_request_tenant_id(request, user)

            # 4.3 验证租户归属（超管直接放行，普通用户需验证）
            if not await self._validate_tenant_access(user, request_tenant_id):
                return JSONResponse(
                    status_code=403,
                    content={"code": 403, "msg": "无权访问该租户", "data": None}
                )

            # 4.4 确定有效租户ID
            effective_tenant_id = request_tenant_id if request_tenant_id > 0 else user.current_tenant_id
            if effective_tenant_id <= 0:
                # 如果用户没有当前租户，尝试获取第一个关联租户
                tenant_ids = await RelationQuery.get_tenant_ids_by_user_id(user.id)
                if tenant_ids:
                    effective_tenant_id = tenant_ids[0]

            # 4.5 设置上下文
            Ctx.set_user(user)
            Ctx.set_request_tenant_id(effective_tenant_id)
            set_tenant_id(effective_tenant_id)

            # 4.6 权限验证（base 接口跳过）
            if not self._is_base_api(path):
                has_perm = await self._check_permission(request, user, effective_tenant_id)
                if not has_perm:
                    return JSONResponse(
                        status_code=403,
                        content={"code": 403, "msg": "无权限访问", "data": None}
                    )

        except Exception as e:
            error_msg = str(e)
            if "Authentication" in error_msg or "Token" in error_msg or "expired" in error_msg:
                return JSONResponse(
                    status_code=401,
                    content={"code": 401, "msg": error_msg, "data": None}
                )
            raise

        response = await call_next(request)
        Ctx.clear()

        return response

    async def _get_request_tenant_id(self, request: Request, user: User) -> int:
        """从请求中获取租户ID

        获取优先级：
        1. 请求头 X-Tenant-ID
        2. 请求头 x-tenant-id (小写兼容)
        3. Query 参数 tenant_id
        4. Body 参数 tenant_id (仅 POST/PUT/PATCH)
        5. 从 user.current_tenant_id 获取
        """
        # 1. 从 Header 获取 (X-Tenant-ID 或 x-tenant-id)
        tenant_id_header = request.headers.get("X-Tenant-ID") or request.headers.get("x-tenant-id")
        if tenant_id_header:
            try:
                return int(tenant_id_header)
            except ValueError:
                pass

        # 2. 从 Query 获取
        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            try:
                return int(tenant_id)
            except ValueError:
                pass

        # 3. 从 Body 获取 (仅 POST/PUT/PATCH)
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
                tenant_id = body.get("tenant_id")
                if tenant_id:
                    return int(tenant_id)
            except Exception:
                pass

        # 4. 从 user 中获取当前租户ID
        return getattr(user, "current_tenant_id", 0)

    async def _validate_tenant_access(self, user: User, tenant_id: int) -> bool:
        """
        验证用户是否有权访问指定租户
        
        - 超管：直接放行
        - 普通用户：查询关联表判断是否拥有该租户
        - tenant_id <= 0：表示不过滤，放行
        """
        # tenant_id <= 0 表示不过滤，放行
        if tenant_id <= 0:
            return True
        
        # 超管直接放行
        if user.is_superuser:
            return True
        
        # 普通用户：查询关联表判断是否拥有该租户
        user_tenant_ids = await RelationQuery.get_tenant_ids_by_user_id(user.id)
        return tenant_id in user_tenant_ids

    async def _check_permission(self, request: Request, user: User, tenant_id: int) -> bool:
        """检查用户是否有权限访问当前接口"""
        from app.models.admin import Api
        from app.services.permission_cache_service import permission_cache_service
        
        if user.is_superuser:
            return True

        method = request.method
        path = request.url.path

        try:
            # 使用权限缓存服务获取用户权限
            permission_apis = await permission_cache_service.get_user_permissions(user.id, tenant_id)

            if permission_apis is None:
                return False

            # 获取当前请求的API code
            current_api = await Api.filter(method=method, path=path).first()
            if not current_api:
                return False

            return current_api.api_code in permission_apis

        except Exception:
            # 降级处理：直接从数据库获取权限
            role_ids = await RelationQuery.get_role_ids_by_user_id(user.id)
            if not role_ids:
                return False

            api_ids_mapping = await RelationQuery.batch_get_api_ids_by_role_ids(role_ids)
            all_api_ids = list({aid for ids in api_ids_mapping.values() for aid in ids})

            if not all_api_ids:
                return False

            apis = await Api.filter(id__in=all_api_ids).values("api_code")
            permission_apis = {api["api_code"] for api in apis}

            current_api = await Api.filter(method=method, path=path).first()
            if not current_api:
                return False

            return current_api.api_code in permission_apis


class RequestLoggingMiddleware:
    """
    请求日志记录中间件 - 只记录请求/响应信息，不记录异常
    异常由 Exception Handler 统一处理
    """

    def __init__(self, app: ASGIApp):
        self.app = app
        from app.settings import settings
        self.skip_paths = set(settings.LOG_SKIP_PATHS or [])
        self.sensitive_fields = set(settings.LOG_SENSITIVE_FIELDS or [])
        self.max_field_length = settings.LOG_MAX_FIELD_LENGTH
        self.max_body_length = settings.LOG_MAX_BODY_LENGTH

    def _should_skip_logging(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.skip_paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if self._should_skip_logging(path):
            await self.app(scope, receive, send)
            return

        # 注意：app_type 已由子应用的 SetAppTypeMiddleware 设置
        # 这里不需要再根据路径判断

        start_time = datetime.now()

        headers = dict(scope.get("headers", []))
        client_ip = self._get_client_ip_from_scope(scope, headers)
        tenant_id = Ctx.get_effective_tenant_id()
        set_tenant_id(tenant_id)

        request_body = None
        receive_buffer = []

        async def wrapped_receive() -> Message:
            nonlocal request_body
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                if body:
                    receive_buffer.append(body)
                if not message.get("more_body", False):
                    full_body = b"".join(receive_buffer)
                    request_body = self._parse_request_body(full_body, headers)
            return message

        response_body_chunks = []
        response_status = None

        async def wrapped_send(message: Message) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message.get("status")
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                if body:
                    response_body_chunks.append(body)
            await send(message)

        await self.app(scope, wrapped_receive, wrapped_send)

        duration = (datetime.now() - start_time).total_seconds() * 1000

        response_body = None
        if response_body_chunks:
            full_body = b"".join(response_body_chunks)
            response_body = self._parse_response_body(full_body)

        log_data = {
            "event": "http_request",
            "method": scope.get("method", ""),
            "path": path,
            "status_code": response_status or 200,
            "elapsed_time": round(duration, 2),
            "client_ip": client_ip,
        }

        if tenant_id:
            log_data["tenant_id"] = tenant_id
        if request_body:
            log_data["request_params"] = request_body
        if response_body:
            log_data["response"] = response_body

        logger.info(**log_data)

    def _parse_request_body(self, body: bytes, headers: dict) -> dict:
        try:
            if not body:
                return {}

            content_type = headers.get(b"content-type", b"").decode("utf-8", errors="ignore")
            if "application/json" not in content_type:
                return {}

            data = json.loads(body)
            return self._sanitize(data) if isinstance(data, dict) else {"_data": data}
        except Exception:
            return {}

    def _parse_response_body(self, body: bytes) -> Any:
        try:
            if not body:
                return None

            if len(body) > self.max_body_length:
                return {"_note": f"Response too large ({len(body)} bytes)"}

            data = json.loads(body)
            return self._sanitize(data)
        except Exception:
            return None

    def _get_client_ip_from_scope(self, scope: Scope, headers: dict) -> str:
        forwarded = headers.get(b"x-forwarded-for", b"").decode("utf-8", errors="ignore")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = headers.get(b"x-real-ip", b"").decode("utf-8", errors="ignore")
        if real_ip:
            return real_ip
        client = scope.get("client")
        if client:
            return client[0]
        return "unknown"

    def _sanitize(self, data: Any) -> Any:
        if isinstance(data, dict):
            result = {}
            for k, v in data.items():
                if any(s in k.lower() for s in self.sensitive_fields):
                    result[k] = "***"
                else:
                    result[k] = self._sanitize(v)
            return result
        elif isinstance(data, list):
            return [self._sanitize(item) for item in data]
        elif isinstance(data, str) and len(data) > self.max_field_length:
            return data[:self.max_field_length] + "..."
        return data


class HttpAuditLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, methods: list[str], exclude_paths: list[str]):
        super().__init__(app)
        self.methods = methods
        from app.settings import settings
        self.exclude_paths = list(exclude_paths) + list(settings.AUDIT_LOG_EXCLUDE_PATHS or [])
        self.sensitive_fields = set(settings.LOG_SENSITIVE_FIELDS or ["password", "token", "secret", "key", "auth", "authorization", "cookie"])
        self.max_body_size = settings.LOG_RESPONSE_SIZE_LIMIT
        self.max_field_length = settings.LOG_MAX_FIELD_LENGTH
        self.max_body_length = settings.LOG_MAX_BODY_LENGTH

    def _truncate_value(self, value: Any) -> Any:
        if isinstance(value, str) and len(value) > self.max_field_length:
            return value[:self.max_field_length] + f"... [truncated, total {len(value)} chars]"
        return value

    def _sanitize_and_truncate(self, data: Any) -> Any:
        if isinstance(data, dict):
            result = {}
            for k, v in data.items():
                if any(s in k.lower() for s in self.sensitive_fields):
                    result[k] = "***"
                else:
                    result[k] = self._sanitize_and_truncate(v)
            return result
        elif isinstance(data, list):
            return [self._sanitize_and_truncate(item) for item in data]
        else:
            return self._truncate_value(data)

    async def get_request_args(self, request: Request, request_body: bytes = None) -> dict:
        args = {}
        for key, value in request.query_params.items():
            args[key] = self._truncate_value(value)

        if hasattr(request.state, 'path_params'):
            for k, v in request.state.path_params.items():
                args[k] = self._truncate_value(v)

        if request.method in ["POST", "PUT", "PATCH"] and request_body:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    if len(request_body) > self.max_body_length:
                        args["_note"] = f"Request body too large ({len(request_body)} bytes), truncated"
                        body_data = json.loads(request_body)
                        args.update(self._sanitize_and_truncate(body_data))
                    else:
                        body_data = json.loads(request_body)
                        if isinstance(body_data, dict):
                            args.update(self._sanitize_and_truncate(body_data))
                except Exception:
                    pass

        return args
    
    def should_log(self, request: Request, response: Response) -> bool:
        if request.method not in self.methods:
            return False
        
        path = request.url.path
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return False
        return True

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        from app.core.dependency import AuthControl

        request_body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                request_body = await request.body()
                if request_body and len(request_body) > self.max_body_size:
                    request_body = None
            except Exception:
                pass

        response = await call_next(request)

        try:
            if not self.should_log(request, response):
                return response

            user = None
            try:
                token = request.headers.get("token")
                if token:
                    user = await AuthControl.is_authed(token)
            except Exception:
                pass

            args = await self.get_request_args(request, request_body)

            audit_log = AuditLog(
                user_id=user.id if user else 0,
                username=user.username if user else "anonymous",
                module=request.url.path.split("/")[3] if len(request.url.path.split("/")) > 3 else "",
                summary=f"{request.method} {request.url.path}",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                response_time=0,
                request_args=args,
            )
            await audit_log.save()

        except Exception:
            pass

        return response
