import json
import uuid
from datetime import datetime
from typing import Any

from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send, Message

from app.core.ctx import Ctx
from app.core.dependency import AuthControl
from app.log import logger, set_request_id, set_tenant_id, get_caller_location, is_request_logged, set_request_logged
from app.models.admin import AuditLog, User

from .bgtask import BgTasks


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
    租户上下文中间件

    功能：
    1. 在请求开始时从 Header 获取 token 进行认证
    2. 设置 Ctx（用户和租户ID）
    3. 将用户信息和租户ID存储到请求状态中
    4. 请求结束后清理租户上下文
    """

    def __init__(self, app, exclude_paths: list[str] = None):
        super().__init__(app)
        from app.settings import settings
        if exclude_paths is not None:
            self.exclude_paths = exclude_paths
        else:
            self.exclude_paths = settings.TENANT_EXCLUDE_PATHS or [
                "/docs",
                "/openapi.json",
                "/redoc",
                "/health",
                "/uploads/",
                "/api/autofill/llm/rule/execute",
                "/api/autofill/llm/rule/execute/result",
            ]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        if any(path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        request.state.current_user = None
        request.state.tenant_id = 0
        request.state.is_authenticated = False

        token = request.headers.get("token")

        effective_tenant_id = 0
        if token:
            try:
                user = await AuthControl.is_authed(token)
                request_tenant_id = await self._get_request_tenant_id(request, user)
                jwt_tenant_id = getattr(user, "current_tenant_id", 0)

                Ctx.set_user(user)
                Ctx.set_jwt_tenant_id(jwt_tenant_id)
                if user.is_superuser:
                    Ctx.set_request_tenant_id(request_tenant_id)
                    effective_tenant_id = request_tenant_id if request_tenant_id > 0 else 0
                else:
                    effective_tenant_id = jwt_tenant_id

                # 设置日志模块的 tenant_id
                set_tenant_id(effective_tenant_id)

                request.state.current_user = user
                request.state.tenant_id = effective_tenant_id
                request.state.is_authenticated = True

            except Exception:
                pass

        response = await call_next(request)
        Ctx.clear()

        return response

    async def _get_request_tenant_id(self, request: Request, user) -> int:
        if user.is_superuser:
            tenant_id_header = request.headers.get("X-Tenant-ID")
            if tenant_id_header:
                try:
                    return int(tenant_id_header)
                except ValueError:
                    pass

            tenant_id = request.query_params.get("tenant_id")
            if tenant_id:
                try:
                    return int(tenant_id)
                except ValueError:
                    pass

            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.json()
                    tenant_id = body.get("tenant_id")
                    if tenant_id:
                        return int(tenant_id)
                except Exception:
                    pass

            return 0

        return getattr(user, "current_tenant_id", 0)


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
