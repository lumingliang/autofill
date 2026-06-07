import asyncio

from fastapi import FastAPI
from tortoise.expressions import Q

from app.core.kafka.consumer import shutdown_kafka_consumers

from app.core.exceptions import (
    AllExceptionHandle,
    BusinessException,
    BusinessExceptionHandle,
    DoesNotExist,
    DoesNotExistHandle,
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
    app.add_exception_handler(Exception, AllExceptionHandle)


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
    
    1. 首先注册所有菜单到 menu_registry
    2. 然后同步到数据库
    3. 最后将菜单关联到超级管理员角色
    """
    # 1. 注册所有菜单到 registry
    register_all_menus()
    
    # 2. 同步菜单到数据库
    await menu_registry.sync_to_database()
    
    logger.info("Menus initialized successfully")


async def init_db_data(app=None):
    """初始化数据库基础数据"""
    await init_superuser()
    await init_menus()


async def init_kafka_consumers():
    """初始化 Kafka 消费者"""
    try:
        from app.core.kafka.consumer import init_kafka_consumers as _init_kafka_consumers
        from app.core.kafka.batch_test_consumer import register_batch_test_consumer
        import asyncio

        # 注册批量测试消费者
        register_batch_test_consumer()

        # 启动所有消费者
        _init_kafka_consumers(loop=asyncio.get_event_loop())
        logger.info("Kafka consumers initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Kafka consumers: {e}")


async def close_kafka_consumers():
    """关闭 Kafka 消费者"""
    try:
        await shutdown_kafka_consumers()
        logger.info("Kafka consumers shutdown")
    except Exception as e:
        logger.warning(f"Error shutting down Kafka consumers: {e}")
