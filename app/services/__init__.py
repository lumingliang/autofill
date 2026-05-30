"""
服务层模块

服务模块按功能领域组织：
- system: 系统管理服务（用户、租户、角色、菜单等）
- llm: LLM 相关服务（代理、结构化输出、配置同步）
- autofill: 智能填单服务（AI 填单、Prompt 组装）
- storage: 存储服务（文件管理）
"""

from app.services.system import role_service, tenant_service, user_service

__all__ = [
    "role_service",
    "tenant_service",
    "user_service",
]
