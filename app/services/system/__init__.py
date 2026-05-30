"""
System Services 模块

包含用户管理、租户管理等系统管理相关的 Service
"""

from app.services.system.tenant_service import TenantService
from app.services.system.user_service import UserService

# 创建服务实例
tenant_service = TenantService()
user_service = UserService()

__all__ = ["TenantService", "UserService", "tenant_service", "user_service"]
