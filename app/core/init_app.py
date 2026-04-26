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
    DoesNotExist,
    DoesNotExistHandle,
    HTTPException,
    HttpExcHandle,
    IntegrityError,
    IntegrityHandle,
    RequestValidationError,
    RequestValidationHandle,
    ResponseValidationError,
    ResponseValidationHandle,
)
from app.core.kafka.consumer import get_consumer_manager
from app.core.relation import RelationQuery
from app.log import logger
from app.models.admin import Api, Menu, Role
from app.schemas.menus import MenuType
from app.services.ai_fill_service import AIFillService, get_ai_fill_service
from app.settings.config import settings

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
    app.add_exception_handler(DoesNotExist, DoesNotExistHandle)
    app.add_exception_handler(HTTPException, HttpExcHandle)
    app.add_exception_handler(IntegrityError, IntegrityHandle)
    app.add_exception_handler(RequestValidationError, RequestValidationHandle)
    app.add_exception_handler(ResponseValidationError, ResponseValidationHandle)


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
    menus = await Menu.exists()
    if not menus:
        parent_menu = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="系统管理",
            path="/system",
            order=1,
            parent_id=0,
            icon="carbon:gui-management",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/system/user",
        )
        children_menu = [
            Menu(
                menu_type=MenuType.MENU,
                name="用户管理",
                path="user",
                order=1,
                parent_id=parent_menu.id,
                icon="material-symbols:person-outline-rounded",
                is_hidden=False,
                component="/system/user",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="角色管理",
                path="role",
                order=2,
                parent_id=parent_menu.id,
                icon="carbon:user-role",
                is_hidden=False,
                component="/system/role",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="菜单管理",
                path="menu",
                order=3,
                parent_id=parent_menu.id,
                icon="material-symbols:list-alt-outline",
                is_hidden=False,
                component="/system/menu",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="API管理",
                path="api",
                order=4,
                parent_id=parent_menu.id,
                icon="ant-design:api-outlined",
                is_hidden=False,
                component="/system/api",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="部门管理",
                path="dept",
                order=5,
                parent_id=parent_menu.id,
                icon="mingcute:department-line",
                is_hidden=False,
                component="/system/dept",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="审计日志",
                path="auditlog",
                order=6,
                parent_id=parent_menu.id,
                icon="ph:clipboard-text-bold",
                is_hidden=False,
                component="/system/auditlog",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="租户管理",
                path="tenant",
                order=7,
                parent_id=parent_menu.id,
                icon="material-symbols:domain",
                is_hidden=False,
                component="/system/tenant",
                keepalive=False,
            ),
        ]
        await Menu.bulk_create(children_menu)
        await Menu.create(
            menu_type=MenuType.MENU,
            name="一级菜单",
            path="/top-menu",
            order=2,
            parent_id=0,
            icon="material-symbols:featured-play-list-outline",
            is_hidden=False,
            component="/top-menu",
            keepalive=False,
            redirect="",
        )

        # 创建智能填单菜单
        autofill_menu = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="智能填单",
            path="/autofill",
            order=3,
            parent_id=0,
            icon="material-symbols:smart-toy-outline",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/autofill/app",
        )
        autofill_children = [
            Menu(
                menu_type=MenuType.MENU,
                name="应用管理",
                path="app",
                order=1,
                parent_id=autofill_menu.id,
                icon="material-symbols:apps-outline",
                is_hidden=False,
                component="/autofill/app",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="总结模板",
                path="template",
                order=2,
                parent_id=autofill_menu.id,
                icon="material-symbols:description-outline",
                is_hidden=False,
                component="/autofill/template",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="下拉选项",
                path="dropdown",
                order=3,
                parent_id=autofill_menu.id,
                icon="material-symbols:arrow-drop-down-circle-outline",
                is_hidden=False,
                component="/autofill/dropdown",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="填单记录",
                path="record",
                order=4,
                parent_id=autofill_menu.id,
                icon="material-symbols:history-outline",
                is_hidden=False,
                component="/autofill/record",
                keepalive=False,
            ),
        ]
        await Menu.bulk_create(autofill_children)


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
    await init_roles()
