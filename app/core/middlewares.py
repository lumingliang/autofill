
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


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    租户上下文中间件

    功能：
    1. 在请求开始时从 Header 获取 token 进行认证
    2. 设置 Ctx（用户和租户ID）
    3. 将用户信息和租户ID存储到请求状态中
    4. 请求结束后清理租户上下文

    使用方式：
    - API Handler 直接从 request.state 获取 current_user 和 tenant_id
    - Service/Repository 层从 Ctx 获取租户信息
    - 不需要在 API 层重复调用 AuthControl.is_authed()
    """

    def __init__(self, app, exclude_paths: list[str] = None):
        super().__init__(app)
        # 从配置加载排除路径，如果传入则使用传入的
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

        # 跳过不需要认证的路径
        if any(path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        # 初始化请求状态
        request.state.current_user = None
        request.state.tenant_id = 0
        request.state.is_authenticated = False

        # 获取 token
        token = request.headers.get("token")

        if token:
            try:
                # 调用认证逻辑
                user = await AuthControl.is_authed(token)

                # 从请求参数或查询参数获取租户ID（用于超管指定租户）
                request_tenant_id = await self._get_request_tenant_id(request, user)
                jwt_tenant_id = getattr(user, "current_tenant_id", 0)

                # 设置 Ctx 上下文
                Ctx.set_user(user)
                Ctx.set_jwt_tenant_id(jwt_tenant_id)
                if user.is_superuser:
                    Ctx.set_request_tenant_id(request_tenant_id)

                # 存储到请求状态，供 API Handler 直接使用
                request.state.current_user = user
                request.state.tenant_id = request_tenant_id if user.is_superuser else jwt_tenant_id
                request.state.is_authenticated = True

            except Exception as e:
                # 认证失败时继续处理，但不设置上下文
                logger.warning(f"TenantContextMiddleware: Authentication failed for path {path}: {e}")

        # 处理请求
        response = await call_next(request)

        # 请求结束后清理租户上下文
        Ctx.clear()

        return response

    async def _get_request_tenant_id(self, request: Request, user) -> int:
        """
        从请求中获取租户ID

        优先级：
        1. 请求头 X-Tenant-ID（前端统一传递）
        2. 查询参数 tenant_id（兼容旧代码）
        3. JSON 请求体 tenant_id（兼容旧代码）
        4. 用户当前的租户ID（仅普通用户）

        Args:
            request: 请求对象
            user: 当前用户

        Returns:
            int: 租户ID，0表示不限制（超级管理员未指定租户时）
        """
        # 超级管理员可以指定租户
        if user.is_superuser:
            # 1. 从请求头 X-Tenant-ID 获取（前端统一传递）
            tenant_id_header = request.headers.get("X-Tenant-ID")
            if tenant_id_header:
                try:
                    return int(tenant_id_header)
                except ValueError:
                    pass

            # 2. 从查询参数获取（兼容旧代码）
            tenant_id = request.query_params.get("tenant_id")
            if tenant_id:
                try:
                    return int(tenant_id)
                except ValueError:
                    pass

            # 3. 从请求体获取（需要在调用前预加载，兼容旧代码）
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.json()
                    tenant_id = body.get("tenant_id")
                    if tenant_id:
                        return int(tenant_id)
                except Exception:
                    pass

            # 超级管理员未指定租户，返回0（表示不限制）
            return 0

        # 普通用户使用自己的租户ID
        return getattr(user, "current_tenant_id", 0)


class RequestLoggingMiddleware:
    """
    请求日志记录中间件 - 统一记录入参、出参和异常信息

    设计原则：
    1. 使用结构化JSON日志，便于日志收集和分析
    2. 自动过滤敏感字段（密码、token等）
    3. 限制大响应体的日志大小
    4. 与loguru集成，复用日志配置
    """

    # 响应体大小限制（字符数）- 已从配置加载
    MAX_RESPONSE_LOG_SIZE = 10000  # 10KB

    def __init__(self, app: ASGIApp):
        self.app = app
        # 从配置加载
        from app.settings import settings
        self.skip_paths = set(settings.LOG_SKIP_PATHS or [])
        self.sensitive_fields = set(settings.LOG_SENSITIVE_FIELDS or [])
        self.exclude_paths = set(settings.AUDIT_LOG_EXCLUDE_PATHS or [])
        self.max_field_length = settings.LOG_MAX_FIELD_LENGTH
        self.max_body_length = settings.LOG_MAX_BODY_LENGTH
        self.max_response_log_size = settings.LOG_RESPONSE_SIZE_LIMIT

    def _should_skip_logging(self, path: str) -> bool:
        """检查是否应该跳过日志记录"""
        # 检查配置跳过路径
        if any(path.startswith(p) for p in self.skip_paths):
            return True
        # 检查配置排除路径
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 跳过健康检查、静态资源和配置的排除路径
        path = scope.get("path", "")
        if self._should_skip_logging(path):
            await self.app(scope, receive, send)
            return

        start_time = datetime.now()

        # 获取请求信息
        headers = dict(scope.get("headers", []))
        client_ip = self._get_client_ip_from_scope(scope, headers)
        user_agent = headers.get(b"user-agent", b"").decode("utf-8", errors="ignore")
        tenant_domain = "root"  # 简化处理，后续可从token解析

        # 设置租户域名到上下文变量
        set_tenant_domain(tenant_domain)

        # 用于缓存请求体
        request_body = None
        receive_buffer = []

        # 包装 receive 来捕获请求体
        async def wrapped_receive() -> Message:
            nonlocal request_body
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                if body:
                    receive_buffer.append(body)
                if not message.get("more_body", False):
                    # 请求体接收完毕
                    full_body = b"".join(receive_buffer)
                    request_body = self._parse_request_body(full_body, headers)
            return message

        # 用于捕获响应体
        response_body_chunks = []
        response_status = None
        response_headers = None

        # 包装 send 函数来捕获响应体
        async def wrapped_send(message: Message) -> None:
            nonlocal response_status, response_headers
            if message["type"] == "http.response.start":
                response_status = message.get("status")
                response_headers = message.get("headers", [])
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                if body:
                    response_body_chunks.append(body)
            await send(message)

        try:
            # 调用应用处理请求
            await self.app(scope, wrapped_receive, wrapped_send)

            duration = (datetime.now() - start_time).total_seconds() * 1000

            # 解析响应体
            response_body = None
            if response_body_chunks:
                full_body = b"".join(response_body_chunks)
                response_body = self._parse_response_body(full_body, response_headers)

            # 构建日志数据
            log_data = {
                "method": scope.get("method", ""),
                "path": path,
                "query": scope.get("query_string", b"").decode("utf-8", errors="ignore"),
                "status_code": response_status or 200,
                "duration_ms": round(duration, 2),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "tenant_domain": tenant_domain,
                "request_params": request_body or {},
            }

            # 记录响应体
            if response_body:
                log_data["response"] = response_body

            logger.bind(**log_data).info(f"{scope.get('method', '')} {path} - {response_status or 200}")

        except Exception as exc:
            duration = (datetime.now() - start_time).total_seconds() * 1000

            logger.bind(
                method=scope.get("method", ""),
                path=path,
                query=scope.get("query_string", b"").decode("utf-8", errors="ignore"),
                request_params=request_body or {},
                status_code=500,
                duration_ms=round(duration, 2),
                client_ip=client_ip,
                user_agent=user_agent,
                tenant_domain=tenant_domain,
                error=str(exc),
                error_type=type(exc).__name__,
            ).error(f"{scope.get('method', '')} {path} - 500 - {str(exc)}")
            raise

    def _parse_request_body(self, body: bytes, headers: dict) -> dict:
        """解析请求体"""
        try:
            if not body:
                return {}

            # 检查 content-type
            content_type = headers.get(b"content-type", b"").decode("utf-8", errors="ignore")
            if "application/json" not in content_type:
                return {}

            data = json.loads(body)
            return self._sanitize(data) if isinstance(data, dict) else {"_data": data}
        except Exception:
            return {}

    def _parse_response_body(self, body: bytes, headers: list) -> Any:
        """解析响应体内容"""
        try:
            if not body:
                return None

            # 检查 content-type
            content_type = ""
            for name, value in headers or []:
                if name.lower() == b"content-type":
                    content_type = value.decode("utf-8", errors="ignore")
                    break

            if not content_type.startswith("application/json"):
                return None

            # 先检查原始body大小，超过限制直接返回提示
            if len(body) > self.max_response_log_size:
                return {"_note": f"Response too large ({len(body)} bytes), skipped logging"}

            data = json.loads(body)
            # 应用大小限制和字段截断
            body_str = json.dumps(data, ensure_ascii=False)
            if len(body_str) > self.max_body_length:
                return {"_note": f"Response body too large ({len(body_str)} chars), skipped detailed logging"}

            # 对响应数据进行敏感字段过滤和长度截断
            return self._sanitize(data)
        except Exception:
            return None

    def _get_client_ip_from_scope(self, scope: Scope, headers: dict) -> str:
        """从 scope 获取客户端真实 IP"""
        # 从 headers 获取
        forwarded = headers.get(b"x-forwarded-for", b"").decode("utf-8", errors="ignore")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = headers.get(b"x-real-ip", b"").decode("utf-8", errors="ignore")
        if real_ip:
            return real_ip
        # 从 client 获取
        client = scope.get("client")
        if client:
            return client[0]
        return "unknown"

    def _truncate_value(self, value: Any) -> Any:
        """截断过长的字符串值"""
        if isinstance(value, str) and len(value) > self.max_field_length:
            return value[:self.max_field_length] + f"... [truncated, total {len(value)} chars]"
        return value

    def _sanitize(self, data: Any) -> Any:
        """递归过滤敏感数据并截断过长的值"""
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
        else:
            return self._truncate_value(data)


class HttpAuditLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, methods: list[str], exclude_paths: list[str]):
        super().__init__(app)
        self.methods = methods
        # 合并传入的排除路径和配置文件的排除路径
        from app.settings import settings
        self.exclude_paths = list(exclude_paths) + list(settings.AUDIT_LOG_EXCLUDE_PATHS or [])
        # 从配置加载特殊路径和敏感字段
        self.audit_log_paths = settings.AUDIT_LOG_SPECIAL_PATHS or ["/api/v1/auditlog/list"]
        self.sensitive_fields = set(settings.LOG_SENSITIVE_FIELDS or ["password", "token", "secret", "key", "auth", "authorization", "cookie"])
        # 从配置加载大小限制
        self.max_body_size = settings.LOG_RESPONSE_SIZE_LIMIT  # 100KB
        self.max_field_length = settings.LOG_MAX_FIELD_LENGTH  # 2000字符
        self.max_body_length = settings.LOG_MAX_BODY_LENGTH    # 50KB

    def _truncate_value(self, value: Any) -> Any:
        """截断过长的字符串值"""
        if isinstance(value, str) and len(value) > self.max_field_length:
            return value[:self.max_field_length] + f"... [truncated, total {len(value)} chars]"
        return value

    def _sanitize_and_truncate(self, data: Any) -> Any:
        """递归过滤敏感数据并截断过长的值"""
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
        # 获取查询参数
        for key, value in request.query_params.items():
            args[key] = self._truncate_value(value)

        # 获取路径参数
        if hasattr(request.state, 'path_params'):
            for k, v in request.state.path_params.items():
                args[k] = self._truncate_value(v)

        # 获取请求体
        if request.method in ["POST", "PUT", "PATCH"] and request_body:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    # 检查请求体大小
                    if len(request_body) > self.max_body_length:
                        args["_note"] = f"Request body too large ({len(request_body)} bytes), truncated"
                        # 尝试解析并截断
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
        """判断是否需要记录审计日志"""
        # 只记录指定的 HTTP 方法
        if request.method not in self.methods:
            return False
        
        # 排除特定路径
        path = request.url.path
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return False
        
        # 只记录成功的请求
        if response.status_code < 200 or response.status_code >= 300:
            return False
        
        return True
    
    async def dispatch(self, request: Request, call_next):
        # 如果不记录日志，直接通过
        path = request.url.path
        if any(path.startswith(p) for p in self.exclude_paths) or request.method not in self.methods:
            return await call_next(request)
        
        # 提前读取请求体，避免重复读取
        request_body = b""
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                request_body = await request.body()
        except Exception:
            pass
        
        # 调用下一个中间件
        response = await call_next(request)
        
        # 检查是否需要记录
        if not self.should_log(request, response):
            return response
        
        # 获取请求参数
        request_args = await self.get_request_args(request, request_body)
        
        # 获取响应内容
        response_body = b""
        if hasattr(response, 'body_iterator'):
            async for chunk in response.body_iterator:
                response_body += chunk
            
            # 重新构建响应
            response = Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
        
        # 解析响应内容
        response_content = ""
        try:
            if len(response_body) < self.max_body_size:
                response_text = response_body.decode('utf-8')
                # 尝试解析JSON并应用敏感字段过滤和截断
                try:
                    response_json = json.loads(response_text)
                    truncated_response = self._sanitize_and_truncate(response_json)
                    # 限制最终字符串长度
                    response_str = json.dumps(truncated_response, ensure_ascii=False)
                    if len(response_str) > self.max_body_length:
                        response_content = json.dumps({"_note": f"Response too large, truncated to {self.max_body_length} chars"})
                    else:
                        response_content = response_str
                except json.JSONDecodeError:
                    # 非JSON响应，直接截断字符串
                    if len(response_text) > self.max_body_length:
                        response_content = response_text[:self.max_body_length] + "... [truncated]"
                    else:
                        response_content = response_text
        except Exception:
            pass
        
        # 获取当前用户信息（优先从请求状态获取，其次重新认证）
        user_id = None
        username = None
        if hasattr(request.state, 'current_user') and request.state.current_user:
            user_obj = request.state.current_user
            user_id = user_obj.id
            username = user_obj.username
        else:
            # 降级处理：重新认证
            try:
                token = request.headers.get("token")
                if token:
                    user_obj: User = await AuthControl.is_authed(token)
                    if user_obj:
                        user_id = user_obj.id
                        username = user_obj.username
            except Exception:
                pass
        
        # 没有用户信息时不记录审计日志（如 API Key 认证）
        if user_id is None:
            return response
        
        # 记录审计日志（后台任务）
        await BgTasks.add_task(
            AuditLog.create,
            user_id=user_id,
            username=username or "",
            method=request.method,
            path=request.url.path,
            ip=self.get_client_ip(request),
            args=request_args,
            response=response_content[:2000]  # 限制长度
        )
        
        return response
    
    def get_client_ip(self, request: Request) -> str:
        """获取客户端 IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"


class LimitRequestMiddleware(BaseHTTPMiddleware):
    """
    请求限制中间件
    用于限制上传文件大小和请求体大小
    """

    def __init__(self, app, max_upload_size: int = 10 * 1024 * 1024):  # 默认10MB
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next):
        # 检查 Content-Length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_upload_size:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": f"请求体大小超过限制: {self.max_upload_size} bytes"}
                    )
            except ValueError:
                pass

        return await call_next(request)
