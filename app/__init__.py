import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
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
from app.settings.config import settings

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

    await init_data()

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
        middleware=make_middlewares(),
        lifespan=lifespan,
    )
    register_exceptions(app)
    register_routers(app, prefix="/api")
    
    # 注册静态文件服务 - 上传文件访问
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")
    
    return app


app = create_app()
