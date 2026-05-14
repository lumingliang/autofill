from fastapi import APIRouter

from app.core.dependency import DependPermission

from .apis import apis_router
from .auditlog import auditlog_router
from .autofill import (
    app_router,
    dropdown_router,
    field_group_router,
    field_spec_router,
    page_router,
    record_router,
    template_router,
    test_fill_router,
    cascade_router,
)
from .base import base_router
from .depts import depts_router
from .menus import menus_router
from .roles import roles_router
from .tenants import tenant_router
from .users import users_router
from .upload import router as upload_router
from .ai.llm_config import llm_config_router
from .byd_dealer import byd_dealer_router

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
v1_router.include_router(template_router, prefix="/autofill", dependencies=[DependPermission], tags=["总结模板管理"])
v1_router.include_router(dropdown_router, prefix="/autofill", dependencies=[DependPermission], tags=["下拉选项管理"])
v1_router.include_router(record_router, prefix="/autofill", dependencies=[DependPermission], tags=["填单记录管理"])

# 智能填单模块 - 页面、字段组、字段管理
v1_router.include_router(page_router, prefix="/autofill", dependencies=[DependPermission], tags=["页面管理"])
v1_router.include_router(field_group_router, prefix="/autofill", dependencies=[DependPermission], tags=["字段组管理"])
v1_router.include_router(field_spec_router, prefix="/autofill", dependencies=[DependPermission], tags=["字段管理"])

# 级联下拉配置
v1_router.include_router(cascade_router, prefix="/autofill", dependencies=[DependPermission], tags=["级联下拉配置"])

# 测试填单模块
v1_router.include_router(test_fill_router, prefix="/autofill", dependencies=[DependPermission], tags=["测试填单"])

# AI 模块 - LLM 配置管理
v1_router.include_router(llm_config_router, prefix="/ai", dependencies=[DependPermission], tags=["LLM配置管理"])

# 比亚迪经销商门店管理（内部 API，需要 JWT 认证）
v1_router.include_router(byd_dealer_router, prefix="/byd-dealers", dependencies=[DependPermission], tags=["比亚迪经销商门店"])
