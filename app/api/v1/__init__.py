from fastapi import APIRouter

from app.core.dependency import DependPermission

from .apis import apis_router
from .auditlog import auditlog_router
from .autofill import (
    app_router,
    field_group_router,
    field_spec_router,
    record_router,
    rule_router,
    rule_test_router,
    rule_import_router,
    test_fill_router,
    system_prompt_router,
)
from .base import base_router
from .depts import depts_router
from .menus import menus_router
from .roles import roles_router
from .tenants import tenant_router
from .users import users_router
from .upload import router as upload_router
from .ai.llm_config import llm_config_router

v1_router = APIRouter()

v1_router.include_router(base_router, prefix="/base")
v1_router.include_router(users_router, prefix="/user", dependencies=[DependPermission])
v1_router.include_router(roles_router, prefix="/role", dependencies=[DependPermission])
v1_router.include_router(menus_router, prefix="/menu", dependencies=[DependPermission])
v1_router.include_router(apis_router, prefix="/api", dependencies=[DependPermission])
v1_router.include_router(depts_router, prefix="/dept", dependencies=[DependPermission])
v1_router.include_router(auditlog_router, prefix="/auditlog", dependencies=[DependPermission])
v1_router.include_router(tenant_router, prefix="/tenant", dependencies=[DependPermission])
v1_router.include_router(upload_router, prefix="/upload")

# 智能填单模块 - 分别设置 tags
v1_router.include_router(app_router, prefix="/autofill", dependencies=[DependPermission], tags=["应用管理"])
v1_router.include_router(record_router, prefix="/autofill", dependencies=[DependPermission], tags=["填单记录管理"])

# 智能填单模块 - 字段组、字段管理（页面管理已删除）
v1_router.include_router(field_group_router, prefix="/autofill", dependencies=[DependPermission], tags=["字段组管理"])
v1_router.include_router(field_spec_router, prefix="/autofill", dependencies=[DependPermission], tags=["字段管理"])

# 测试填单模块
v1_router.include_router(test_fill_router, prefix="/autofill", dependencies=[DependPermission], tags=["测试填单"])

# 规则管理模块
v1_router.include_router(rule_router, prefix="/autofill", dependencies=[DependPermission], tags=["规则管理"])

# 规则测试模块
v1_router.include_router(rule_test_router, prefix="/autofill", dependencies=[DependPermission], tags=["规则测试"])

# 规则导入模块
v1_router.include_router(rule_import_router, prefix="/autofill", dependencies=[DependPermission], tags=["规则导入"])

# 系统提示词管理模块
v1_router.include_router(system_prompt_router, prefix="/autofill", dependencies=[DependPermission], tags=["系统提示词管理"])

# AI 模块 - LLM 配置管理
v1_router.include_router(llm_config_router, prefix="/ai", dependencies=[DependPermission], tags=["LLM配置管理"])
