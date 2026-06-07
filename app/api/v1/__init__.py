from fastapi import APIRouter

from app.core.dependency import DependPermission

from .autofill import (
    app_router,
    batch_test_router,
    dify_agent_router,
    record_router,
    rule_router,
    rule_test_router,
    rule_import_router,
    system_prompt_router,
)
from .base import base_router
from .system import (
    apis_router,
    auditlog_router,
    depts_router,
    menus_router,
    roles_router,
    tenants_router as tenant_router,
    users_router,
)
from .upload import router as upload_router
from .ai.llm_config import llm_config_router

v1_router = APIRouter()

v1_router.include_router(base_router, prefix="/base")
v1_router.include_router(users_router, prefix="/user", dependencies=[DependPermission], tags=["用户管理"])
v1_router.include_router(roles_router, prefix="/role", dependencies=[DependPermission], tags=["角色管理"])
v1_router.include_router(menus_router, prefix="/menu", dependencies=[DependPermission], tags=["菜单管理"])
v1_router.include_router(apis_router, prefix="/api", dependencies=[DependPermission], tags=["API管理"])
v1_router.include_router(depts_router, prefix="/dept", dependencies=[DependPermission], tags=["部门管理"])
v1_router.include_router(auditlog_router, prefix="/auditlog", dependencies=[DependPermission], tags=["审计日志"])
v1_router.include_router(tenant_router, prefix="/tenant", dependencies=[DependPermission], tags=["租户管理"])
v1_router.include_router(upload_router, prefix="/upload", tags=["文件上传"])

# 智能填单模块 - 分别设置 tags
v1_router.include_router(app_router, prefix="/autofill", dependencies=[DependPermission], tags=["应用管理"])
v1_router.include_router(record_router, prefix="/autofill", dependencies=[DependPermission], tags=["填单记录管理"])

# 规则管理模块
v1_router.include_router(rule_router, prefix="/autofill", dependencies=[DependPermission], tags=["规则管理"])

# 规则测试模块
v1_router.include_router(rule_test_router, prefix="/autofill", dependencies=[DependPermission], tags=["规则测试"])

# 规则导入模块
v1_router.include_router(rule_import_router, prefix="/autofill", dependencies=[DependPermission], tags=["规则导入"])

# 系统提示词管理模块
v1_router.include_router(system_prompt_router, prefix="/autofill", dependencies=[DependPermission], tags=["系统提示词管理"])

# Dify Agent 管理模块
v1_router.include_router(dify_agent_router, prefix="/autofill", dependencies=[DependPermission], tags=["Dify Agent 管理"])

# 批量测试模块
v1_router.include_router(batch_test_router, prefix="/batch-test", dependencies=[DependPermission], tags=["批量测试管理"])

# AI 模块 - LLM 配置管理
v1_router.include_router(llm_config_router, prefix="/ai", dependencies=[DependPermission], tags=["LLM配置管理"])
