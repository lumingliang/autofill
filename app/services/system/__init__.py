"""
System Services 模块

包含用户管理、租户管理等系统管理相关的 Service
"""

from app.services.system.api_service import ApiService
from app.services.system.menu_service import MenuService
from app.services.system.tenant_service import TenantService
from app.services.system.user_service import UserService

# 创建服务实例
api_service = ApiService()
menu_service = MenuService()
tenant_service = TenantService()
user_service = UserService()

__all__ = [
    "ApiService",
    "MenuService",
    "TenantService",
    "UserService",
    "api_service",
    "menu_service",
    "tenant_service",
    "user_service",
]
