import json
import re
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.dependency import AuthControl
from app.log import logger, set_request_id, set_tenant_domain
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
        # 从请求头获取或生成请求 ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # 设置到上下文变量
        set_request_id(request_id)

        # 将请求 ID 添加到响应头
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志记录中间件"""

    def __init__(self, app):
        super().__init__(app)

    async def _get_tenant_domain(self, request: Request) -> str:
        """获取租户域名，优先从token中解析，默认为 root"""
        try:
            token = request.headers.get("token")
            if token:
                # 优先从token中直接解析域名，避免查数据库
                import jwt
                from app.settings import settings
                decode_data = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.JWT_ALGORITHM)
                tenant_domain = decode_data.get("tenant_domain")
                if tenant_domain:
                    return tenant_domain
                # 兼容旧token：从token解析用户后查数据库
                user_obj: User = await AuthControl.is_authed(token)
                if user_obj and user_obj.current_tenant_id:
                    from app.models.admin import Tenant
                    tenant = await Tenant.filter(id=user_obj.current_tenant_id).first()
                    if tenant and tenant.domain:
                        return tenant.domain
        except Exception:
            pass
        return "root"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 跳过健康检查和静态资源
        if self._should_skip_logging(request):
            return await call_next(request)

        start_time = datetime.now()

        # 获取请求信息
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        tenant_domain = await self._get_tenant_domain(request)

        # 设置租户域名到上下文变量
        set_tenant_domain(tenant_domain)

        try:
            response = await call_next(request)
            duration = (datetime.now() - start_time).total_seconds() * 1000

            # 记录访问日志
            logger.bind(
                method=request.method,
                path=request.url.path,
                query=str(request.query_params),
                status_code=response.status_code,
                duration_ms=round(duration, 2),
                client_ip=client_ip,
                user_agent=user_agent,
                tenant_domain=tenant_domain,
            ).info(f"{request.method} {request.url.path} - {response.status_code}")

            return response

        except Exception as exc:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            logger.bind(
                method=request.method,
                path=request.url.path,
                query=str(request.query_params),
                status_code=500,
                duration_ms=round(duration, 2),
                client_ip=client_ip,
                user_agent=user_agent,
                tenant_domain=tenant_domain,
                error=str(exc),
            ).error(f"{request.method} {request.url.path} - 500 - {str(exc)}")
            raise

    def _should_skip_logging(self, request: Request) -> bool:
        """检查是否应该跳过日志记录"""
        skip_paths = ["/docs", "/openapi.json", "/redoc", "/health", "/uploads/"]
        return any(request.url.path.startswith(path) for path in skip_paths)

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实 IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"


class HttpAuditLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, methods: list[str], exclude_paths: list[str]):
        super().__init__(app)
        self.methods = methods
        self.exclude_paths = exclude_paths
        self.audit_log_paths = ["/api/v1/auditlog/list"]
        self.max_body_size = 1024 * 1024  # 1MB 响应体大小限制

    async def get_request_args(self, request: Request) -> dict:
        args = {}
        # 获取查询参数
        for key, value in request.query_params.items():
            args[key] = value

        # 获取请求体 - 跳过 multipart/form-data 文件上传
        content_type = request.headers.get("content-type", "")
        if request.method in ["POST", "PUT", "PATCH"]:
            # 完全跳过 multipart/form-data 请求，不读取请求体
            # 因为 request.form() 会消耗请求体，导致后续路由无法读取文件
            if "multipart/form-data" in content_type:
                args["_note"] = "multipart/form-data upload"
                return args

            try:
                body = await request.json()
                args.update(body)
            except json.JSONDecodeError:
                # 对于非 multipart 的表单数据，尝试解析
                try:
                    body = await request.form()
                    for k, v in body.items():
                        if hasattr(v, "filename"):  # 文件上传行为
                            args[k] = f"<file:{v.filename}>"
                        elif isinstance(v, list) and v and hasattr(v[0], "filename"):
                            args[k] = [f"<file:{file.filename}>" for file in v]
                        else:
                            args[k] = str(v)
                except Exception:
                    pass

        return args

    async def get_response_body(self, request: Request, response: Response) -> Any:
        # 检查Content-Type，跳过非JSON内容（如图片、文件等）
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("application/json"):
            return None

        # 检查Content-Length
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            return {"code": 0, "msg": "Response too large to log", "data": None}

        if hasattr(response, "body"):
            body = response.body
        else:
            body_chunks = []
            async for chunk in response.body_iterator:
                if not isinstance(chunk, bytes):
                    chunk = chunk.encode(response.charset)
                body_chunks.append(chunk)

            response.body_iterator = self._async_iter(body_chunks)
            body = b"".join(body_chunks)

        if any(request.url.path.startswith(path) for path in self.audit_log_paths):
            try:
                data = self.lenient_json(body)
                # 只保留基本信息，去除详细的响应内容
                if isinstance(data, dict):
                    data.pop("response_body", None)
                    if "data" in data and isinstance(data["data"], list):
                        for item in data["data"]:
                            item.pop("response_body", None)
                return data
            except Exception:
                return None

        return self.lenient_json(body)

    def lenient_json(self, v: Any) -> Any:
        if isinstance(v, (str, bytes)):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                pass
        return v

    async def _async_iter(self, items: list[bytes]) -> AsyncGenerator[bytes, None]:
        for item in items:
            yield item

    async def get_request_log(self, request: Request, response: Response) -> dict:
        """
        根据request和response对象获取对应的日志记录数据
        """
        data: dict = {"path": request.url.path, "status": response.status_code, "method": request.method}
        # 路由信息
        app: FastAPI = request.app
        for route in app.routes:
            if (
                isinstance(route, APIRoute)
                and route.path_regex.match(request.url.path)
                and request.method in route.methods
            ):
                data["module"] = ",".join(route.tags)
                data["summary"] = route.summary
        # 获取用户信息
        try:
            token = request.headers.get("token")
            user_obj = None
            tenant_domain = None
            if token:
                # 优先从token中解析域名，避免查数据库
                import jwt
                from app.settings import settings
                try:
                    decode_data = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.JWT_ALGORITHM)
                    tenant_domain = decode_data.get("tenant_domain")
                except Exception:
                    pass
                user_obj: User = await AuthControl.is_authed(token)
            data["user_id"] = user_obj.id if user_obj else 0
            data["username"] = user_obj.username if user_obj else ""
            # 记录当前租户ID和域名
            tenant_id = user_obj.current_tenant_id if user_obj else None
            data["tenant_id"] = tenant_id
            # 获取租户域名，优先使用token中的
            if tenant_domain:
                data["tenant_domain"] = tenant_domain
            elif tenant_id:
                from app.models.admin import Tenant
                tenant = await Tenant.filter(id=tenant_id).first()
                data["tenant_domain"] = tenant.domain if tenant else None
            else:
                data["tenant_domain"] = None
        except Exception:
            data["user_id"] = 0
            data["username"] = ""
            data["tenant_id"] = None
            data["tenant_domain"] = None
        return data

    async def before_request(self, request: Request):
        request_args = await self.get_request_args(request)
        request.state.request_args = request_args

    async def after_request(self, request: Request, response: Response, process_time: int):
        if request.method in self.methods:
            for path in self.exclude_paths:
                if re.search(path, request.url.path, re.I) is not None:
                    return
            data: dict = await self.get_request_log(request=request, response=response)
            data["response_time"] = process_time

            data["request_args"] = request.state.request_args
            data["response_body"] = await self.get_response_body(request, response)
            await AuditLog.create(**data)

        return response

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time: datetime = datetime.now()
        await self.before_request(request)
        response = await call_next(request)
        end_time: datetime = datetime.now()
        process_time = int((end_time.timestamp() - start_time.timestamp()) * 1000)
        await self.after_request(request, response, process_time)
        return response
