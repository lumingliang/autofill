import asyncio

from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from tortoise.expressions import Q

from app.core.kafka.consumer import shutdown_kafka_consumers

from app.api import api_router
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
from app.core.relation import RelationQuery
from app.log import logger
from app.models.admin import Api, Menu, Role, User
from app.repositories import user_repository
from app.schemas.menus import MenuType
from app.schemas.users import UserCreate
from app.services.system.user_service import user_service
from app.settings.config import settings
from app.core.menu_registry import menu_registry
from app.core.menu_config import register_all_menus
from app.utils.password import get_password_hash

from .middlewares import (
    BackGroundTaskMiddleware,
    ExceptionHandlingMiddleware,
    HttpAuditLogMiddleware,
    RequestIdMiddleware,
    RequestLoggingMiddleware,
    TenantContextMiddleware,
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
        # 异常捕获中间件放在最外层，确保能捕获所有异常
        Middleware(ExceptionHandlingMiddleware),
        Middleware(RequestIdMiddleware),  # 请求追踪 ID 中间件
        Middleware(TenantContextMiddleware),  # 租户上下文中间件（需要在 RequestLoggingMiddleware 之前执行）
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
    """初始化超级管理员用户"""
    user_exists = await User.exists()
    if not user_exists:
        # 使用 Repository 层直接创建超级管理员
        create_data = {
            "username": "admin",
            "email": "admin@admin.com",
            "password": get_password_hash("123456"),
            "is_active": True,
            "is_superuser": True,
        }
        user = await user_repository.create(create_data)
        logger.info(f"Superuser created: {user.username}")


async def init_menus():
    """
    初始化菜单系统
    使用新的菜单注册中心实现增量同步
    """
    # 注册所有菜单配置
    register_all_menus()

    # 同步到数据库（自动处理新增、更新）
    await menu_registry.sync_to_database()


async def init_db():
    """
    初始化数据库连接
    
    注意：此函数仅初始化数据库连接，不执行任何迁移操作。
    数据库迁移必须手动执行：aerich upgrade
    
    参见文档：docs/DATABASE_MIGRATION.md
    """
    from tortoise import Tortoise
    await Tortoise.init(config=settings.TORTOISE_ORM)
    logger.info("Database initialized (migrations must be run manually)")


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
    from app.core.kafka.batch_test_consumer import handle_batch_test_message
    from app.core.kafka.consumer import get_consumer_manager

    manager = get_consumer_manager()

    # 注册批量测试消费者
    manager.register_consumer(
        name="batch_test_consumer",
        topics=["batch-test-execute"],
        message_handler=handle_batch_test_message
    )

    # 获取当前事件循环并启动所有消费者
    loop = asyncio.get_event_loop()
    manager.start_all(loop=loop)

    logger.info("Kafka 消费者初始化完成")


async def shutdown_kafka():
    """关闭 Kafka 消费者"""
    from app.core.kafka.consumer import get_consumer_manager
    manager = get_consumer_manager()
    manager.stop_all()
    logger.info("Kafka 消费者已关闭")


async def init_data(app: FastAPI):
    await init_db()
    # await init_superuser()
    # await init_menus()
    # await init_apis(app)
    # 不需要初始化角色，手动配置
    # await init_roles()
