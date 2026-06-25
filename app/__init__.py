import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from tortoise import Tortoise

from app.core.exceptions import SettingNotFound
from app.core.init_app import (
    init_db_data,
    init_kafka_consumers,
    shutdown_kafka_consumers,
    register_exceptions,
)
from app.core.redis import redis_client
from app.log import setup_logger, logger
from app.core.app_factory import create_internal_app, create_open_app
from app.api.v1 import v1_router
from app.api.open import open_router

try:
    from app.settings.config import settings
except ImportError:
    raise SettingNotFound("Can not import settings")

from app.api.mcp.rule_engine import get_sse_app as get_rule_engine_mcp_app
from app.api.mcp.form_field import get_sse_app as get_form_field_mcp_app

# 初始化日志配置（只执行一次）
setup_logger()

# MCP SSE 子应用（共享主服务端口）
rule_engine_mcp_app = get_rule_engine_mcp_app()
form_field_mcp_app = get_form_field_mcp_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化 Tortoise ORM
    try:
        from app.settings import TORTOISE_ORM
        await Tortoise.init(config=TORTOISE_ORM)
        logger.info("Tortoise ORM initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Tortoise ORM: {e}")
        raise

    # 初始化 Redis 连接
    try:
        await redis_client.init()
    except Exception as e:
        print(f"Warning: Redis connection failed: {e}")

    # 初始化 Kafka 消费者
    await init_kafka_consumers()

    yield

    # 关闭 Kafka 消费者
    await shutdown_kafka_consumers()

    # 关闭 Redis 连接
    try:
        await redis_client.close()
    except Exception:
        pass

    await Tortoise.close_connections()


def create_app() -> FastAPI:
    """
    创建主 FastAPI 应用 - 子应用挂载版本
    
    架构设计：
    - 主应用：只负责挂载子应用和静态资源，不处理业务逻辑
    - 内部 API 子应用 (/api/v1/*)：JWT 认证，完整中间件栈
      - Swagger UI: /api/v1/docs
      - OpenAPI JSON: /api/v1/openapi.json
    - Open API 子应用 (/api/v1/open/*)：API Key 认证，精简中间件栈
      - Swagger UI: /api/v1/open/docs
      - OpenAPI JSON: /api/v1/open/openapi.json
    
    挂载顺序：先挂载 Open API（路径更长），再挂载 Internal API（路径更短）
    这样 /api/v1/open/xxx 会优先匹配到 Open 子应用
    """
    
    # ============ 创建子应用 ============
    internal_app = create_internal_app()
    open_app = create_open_app()
    
    # 注册路由到子应用
    internal_app.include_router(v1_router)
    open_app.include_router(open_router)
    
    # ============ 创建主应用 ============
    # 主应用不处理业务路由，只挂载子应用
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.VERSION,
        # 主应用不生成 openapi，由子应用各自管理
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    
    # 注册全局异常处理器
    register_exceptions(app)
    
    # ============ 挂载子应用 ============
    # 关键：先挂载路径更长的 Open API，再挂载路径更短的 Internal API
    # FastAPI 的 mount 是从上到下匹配，先匹配到的优先处理
    app.mount("/api/v1/open", open_app)
    app.mount("/api/v1", internal_app)

    # ============ 挂载 MCP SSE 端点（共享端口） ============
    app.mount("/mcp/rule_engine", rule_engine_mcp_app)
    app.mount("/mcp/form_field", form_field_mcp_app)

    # ============ 注册静态文件服务 ============
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")
    
    # 注册本地 Swagger UI 静态资源
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
    swagger_ui_dir = os.path.join(static_dir, "swagger-ui")
    if os.path.exists(swagger_ui_dir):
        app.mount("/static/swagger-ui", StaticFiles(directory=swagger_ui_dir), name="swagger-ui-static")
    
    # 注册前端静态文件服务
    web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")
    if os.path.exists(web_dir):
        from fastapi.responses import FileResponse
        from fastapi import Request

        @app.get("/", include_in_schema=False)
        async def root_redirect():
            return FileResponse(os.path.join(web_dir, "index.html"))

        @app.get("/web/{path:path}", include_in_schema=False)
        async def serve_web_files(request: Request, path: str):
            safe_path = os.path.normpath(path)
            if safe_path.startswith("..") or safe_path.startswith("/"):
                safe_path = safe_path.lstrip("/").lstrip(".")
            
            file_path = os.path.join(web_dir, safe_path)
            
            real_file_path = os.path.realpath(file_path)
            real_web_dir = os.path.realpath(web_dir)
            if not real_file_path.startswith(real_web_dir):
                index_file = os.path.join(web_dir, "index.html")
                if os.path.exists(index_file):
                    return FileResponse(index_file)
                return {"error": "Invalid path"}

            if os.path.exists(real_file_path) and os.path.isfile(real_file_path):
                return FileResponse(real_file_path)

            index_file = os.path.join(web_dir, "index.html")
            if os.path.exists(index_file):
                return FileResponse(index_file)

            return {"error": "Frontend not found"}

    return app


app = create_app()
