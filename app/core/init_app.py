import shutil

from aerich import Command
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from tortoise.expressions import Q

from app.api import api_router
from app.controllers.api import api_controller
from app.controllers.user import UserCreate, user_controller
from app.core.exceptions import (
    BusinessException,
    BusinessExceptionHandle,
    DoesNotExist,
    DoesNotExistHandle,
    GlobalExceptionHandle,
    HTTPException,
    HttpExcHandle,
    IntegrityError,
    IntegrityHandle,
    OperationalError,
    OperationalErrorHandle,
    RequestValidationError,
    RequestValidationHandle,
    ResourceNotFoundException,
    ResponseValidationError,
    ResponseValidationHandle,
    SettingNotFound,
    SettingNotFoundHandle,
    StarletteHTTPException,
    StarletteHttpExcHandle,
    ValidationException,
)
from app.core.kafka.consumer import get_consumer_manager
from app.core.relation import RelationQuery
from app.log import logger
from app.models.admin import Api, Menu, Role
from app.schemas.menus import MenuType
from app.services.autofill.ai_fill_service import AIFillService, get_ai_fill_service
from app.settings.config import settings
from app.core.menu_registry import menu_registry
from app.core.menu_config import register_all_menus

from .middlewares import (
    BackGroundTaskMiddleware,
    HttpAuditLogMiddleware,
    RequestIdMiddleware,
    RequestLoggingMiddleware,
)


def make_middlewares():
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        ),
        Middleware(RequestIdMiddleware),  # 请求追踪 ID 中间件（最先执行）
        Middleware(RequestLoggingMiddleware),  # 请求日志记录中间件
        Middleware(BackGroundTaskMiddleware),
        Middleware(
            HttpAuditLogMiddleware,
            methods=["GET", "POST", "PUT", "DELETE"],
            exclude_paths=[
                "/api/v1/base/access_token",
                "/docs",
                "/openapi.json",
                "/uploads",
            ],
        ),
    ]
    return middleware


def register_exceptions(app: FastAPI):
    """
    注册全局异常处理器
    
    异常处理器按照从具体到一般的顺序注册：
    1. 具体的业务异常（如 BusinessException）
    2. 框架特定异常（如 HTTPException、RequestValidationError）
    3. 数据库异常（如 DoesNotExist、IntegrityError）
    4. 通用异常（Exception）作为最后的兜底
    """
    # 业务异常
    app.add_exception_handler(BusinessException, BusinessExceptionHandle)
    
    # HTTP 异常
    app.add_exception_handler(HTTPException, HttpExcHandle)
    app.add_exception_handler(StarletteHTTPException, StarletteHttpExcHandle)
    
    # 请求/响应验证异常
    app.add_exception_handler(RequestValidationError, RequestValidationHandle)
    app.add_exception_handler(ResponseValidationError, ResponseValidationHandle)
    
    # 数据库异常
    app.add_exception_handler(DoesNotExist, DoesNotExistHandle)
    app.add_exception_handler(IntegrityError, IntegrityHandle)
    app.add_exception_handler(OperationalError, OperationalErrorHandle)
    
    # 配置异常
    app.add_exception_handler(SettingNotFound, SettingNotFoundHandle)
    
    # 通用异常处理器（最后注册，作为兜底）
    app.add_exception_handler(Exception, GlobalExceptionHandle)


def register_routers(app: FastAPI, prefix: str = "/api"):
    app.include_router(api_router, prefix=prefix)


async def init_superuser():
    user = await user_controller.model.exists()
    if not user:
        await user_controller.create_user(
            UserCreate(
                username="admin",
                email="admin@admin.com",
                password="123456",
                is_active=True,
                is_superuser=True,
            )
        )


async def init_menus():
    """
    初始化菜单系统
    使用新的菜单注册中心实现增量同步
    """
    # 注册所有菜单配置
    register_all_menus()

    # 同步到数据库（自动处理新增、更新）
    await menu_registry.sync_to_database()


async def init_apis():
    apis = await api_controller.model.exists()
    if not apis:
        await api_controller.refresh_api()


async def init_db():
    command = Command(tortoise_config=settings.TORTOISE_ORM)
    try:
        await command.init_db(safe=True)
    except FileExistsError:
        pass

    await command.init()
    try:
        await command.migrate()
    except AttributeError:
        logger.warning("unable to retrieve model history from database, model history will be created from scratch")
        shutil.rmtree("migrations")
        await command.init_db(safe=True)

    await command.upgrade(run_in_transaction=True)


async def init_roles():
    roles = await Role.exists()
    if not roles:
        admin_role = await Role.create(
            name="管理员",
            desc="管理员角色",
        )
        user_role = await Role.create(
            name="普通用户",
            desc="普通用户角色",
        )

        # 批量关联所有API给管理员角色
        all_apis = await Api.all().values("id")
        await RelationQuery.batch_add_role_apis([(admin_role.id, a["id"]) for a in all_apis])

        # 批量关联所有菜单给管理员和普通用户
        all_menus = await Menu.all().values("id")
        admin_menu_pairs = [(admin_role.id, m["id"]) for m in all_menus]
        user_menu_pairs = [(user_role.id, m["id"]) for m in all_menus]
        await RelationQuery.batch_add_role_menus(admin_menu_pairs)
        await RelationQuery.batch_add_role_menus(user_menu_pairs)

        # 为普通用户分配基本API
        basic_apis = await Api.filter(Q(method__in=["GET"]) | Q(tags="基础模块")).values("id")
        await RelationQuery.batch_add_role_apis([(user_role.id, a["id"]) for a in basic_apis])


async def init_kafka_consumers():
    """初始化 Kafka 消费者"""
    try:
        logger.info("[KAFKA INIT] Starting Kafka consumers initialization...")
        manager = get_consumer_manager()
        logger.info(f"[KAFKA INIT] Consumer manager created")

        # 注册 AI 填单消费者
        service = get_ai_fill_service()
        topic = AIFillService.AI_FILL_TOPIC
        logger.info(f"[KAFKA INIT] Registering consumer for topic: {topic}")

        manager.register_consumer(
            name="ai_fill_consumer",
            topics=[topic],
            message_handler=service.process_kafka_message,
        )
        logger.info(f"[KAFKA INIT] Consumer registered successfully")

        # 启动所有消费者
        logger.info(f"[KAFKA INIT] Starting all consumers...")
        import asyncio
        loop = asyncio.get_event_loop()
        logger.info(f"[KAFKA INIT] Got event loop: {loop}")
        manager.start_all(loop=loop)
        logger.info("[KAFKA INIT] Kafka consumers initialized successfully")
    except Exception as e:
        logger.error(f"[KAFKA INIT] Failed to initialize Kafka consumers: {e}", exc_info=True)
        # 不阻塞应用启动，只是记录错误


async def shutdown_kafka():
    """关闭 Kafka 消费者"""
    try:
        from app.core.kafka.consumer import shutdown_kafka_consumers
        shutdown_kafka_consumers()
        logger.info("Kafka consumers shutdown successfully")
    except Exception as e:
        logger.error(f"Error shutting down Kafka consumers: {e}")


async def init_data():
    await init_db()
    await init_superuser()
    await init_menus()
    await init_apis()
    # 不需要初始化角色，手动配置
    # await init_roles()
