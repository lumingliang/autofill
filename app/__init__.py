import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from tortoise import Tortoise

from app.core.exceptions import SettingNotFound
from app.core.init_app import (
    init_data,
    init_kafka_consumers,
    shutdown_kafka,
    make_middlewares,
    register_exceptions,
    register_routers,
)
from app.core.redis import redis_client
from app.log import setup_logger

try:
    from app.settings.config import settings
except ImportError:
    raise SettingNotFound("Can not import settings")

# 初始化日志配置（只执行一次）
setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化 Redis 连接
    try:
        await redis_client.init()
    except Exception as e:
        print(f"Warning: Redis connection failed: {e}")

    await init_data(app)

    # 初始化 Kafka 消费者
    await init_kafka_consumers()

    yield

    # 关闭 Kafka 消费者
    await shutdown_kafka()

    # 关闭 Redis 连接
    try:
        await redis_client.close()
    except Exception:
        pass

    await Tortoise.close_connections()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.VERSION,
        openapi_url="/openapi.json",
        docs_url=None,
        redoc_url=None,
        middleware=make_middlewares(),
        lifespan=lifespan,
    )
    register_exceptions(app)
    register_routers(app, prefix="/api")

    # 注册静态文件服务 - 上传文件访问
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

    # 注册本地 Swagger UI 静态资源（内网部署使用）
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
    swagger_ui_dir = os.path.join(static_dir, "swagger-ui")
    if os.path.exists(swagger_ui_dir):
        app.mount("/static/swagger-ui", StaticFiles(directory=swagger_ui_dir), name="swagger-ui-static")

    # 注册前端静态文件服务（Docker 部署使用）
    web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")
    if os.path.exists(web_dir):
        from fastapi.responses import FileResponse
        from fastapi import Request

        # 根路径返回 index.html
        @app.get("/", include_in_schema=False)
        async def root_redirect():
            return FileResponse(os.path.join(web_dir, "index.html"))

        # 处理前端静态文件和 SPA 路由
        @app.get("/web/{path:path}", include_in_schema=False)
        async def serve_web_files(request: Request, path: str):
            """
            处理前端静态文件和 SPA 路由
            - 如果请求的是存在的文件（如 CSS、JS、图片），直接返回文件
            - 否则返回 index.html，由前端路由处理（SPA 模式）
            """
            # 安全路径处理：防止目录遍历攻击
            safe_path = os.path.normpath(path)
            if safe_path.startswith("..") or safe_path.startswith("/"):
                safe_path = safe_path.lstrip("/").lstrip(".")
            
            file_path = os.path.join(web_dir, safe_path)
            
            # 确保路径在 web_dir 范围内（防止目录遍历）
            real_file_path = os.path.realpath(file_path)
            real_web_dir = os.path.realpath(web_dir)
            if not real_file_path.startswith(real_web_dir):
                index_file = os.path.join(web_dir, "index.html")
                if os.path.exists(index_file):
                    return FileResponse(index_file)
                return {"error": "Invalid path"}

            # 检查文件是否存在且是文件（不是目录）
            if os.path.exists(real_file_path) and os.path.isfile(real_file_path):
                return FileResponse(real_file_path)

            # 文件不存在，返回 index.html（SPA 路由）
            index_file = os.path.join(web_dir, "index.html")
            if os.path.exists(index_file):
                return FileResponse(index_file)

            return {"error": "Frontend not found"}

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=f"{settings.APP_TITLE} - Swagger UI",
            swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui/swagger-ui.css",
            swagger_favicon_url="/static/swagger-ui/favicon.png",
        )

    return app


app = create_app()
