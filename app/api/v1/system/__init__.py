"""
System API 模块

包含用户管理、租户管理、角色管理等系统管理相关的 API
"""

from app.api.v1.system.users import router as users_router
from app.api.v1.system.tenants import router as tenants_router
from app.api.v1.system.roles import router as roles_router

__all__ = ["users_router", "tenants_router", "roles_router"]
