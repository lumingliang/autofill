"""
Repository 层 - 数据访问层
提供统一的数据库和 seekdb 查询接口

目录结构:
- base_repository.py - 基础仓库类和通用接口
- system/ - 系统管理相关仓库
  - dept_repository.py - 部门仓库
  - dept_closure_repository.py - 部门闭包关联表仓库
  - role_repository.py - 角色仓库
  - tenant_repository.py - 租户仓库
  - user_repository.py - 用户相关仓库（包含关联表查询）
  - user_role_repository.py - 用户-角色关联表仓库
  - user_tenant_repository.py - 用户-租户关联表仓库
- rule_management/ - 规则管理相关仓库
- autofill/ - 智能填单相关仓库
"""

from .base_repository import BaseRepository
from .rule_management import rule_info_repository, rule_version_repository, rule_data_repository
from .system.api_repository import api_repository
from .system.dept_closure_repository import dept_closure_repository
from .system.dept_repository import dept_repository
from .system.menu_repository import menu_repository
from .system.role_api_repository import role_api_repository
from .system.role_menu_repository import role_menu_repository
from .system.role_repository import role_repository
from .system.tenant_repository import tenant_repository
from .system.user_repository import user_repository
from .system.user_role_repository import user_role_repository
from .system.user_tenant_repository import user_tenant_repository
from .system.audit_log_repository import audit_log_repository

__all__ = [
    "api_repository",
    "audit_log_repository",
    "BaseRepository",
    "dept_closure_repository",
    "dept_repository",
    "menu_repository",
    "role_api_repository",
    "role_menu_repository",
    "role_repository",
    "rule_info_repository",
    "rule_version_repository",
    "rule_data_repository",
    "tenant_repository",
    "user_repository",
    "user_role_repository",
    "user_tenant_repository",
]
