"""
Autofill v1 API 模块

包含应用管理、记录管理、规则管理、规则测试、规则导入、系统提示词管理等 API
"""

from app.api.v1.autofill.app import router as app_router
from app.api.v1.autofill.record import router as record_router
from app.api.v1.autofill.rule import router as rule_router
from app.api.v1.autofill.rule_import import router as rule_import_router
from app.api.v1.autofill.rule_test import router as rule_test_router
from app.api.v1.autofill.system_prompt import router as system_prompt_router

__all__ = [
    "app_router",
    "record_router",
    "rule_router",
    "rule_test_router",
    "rule_import_router",
    "system_prompt_router",
]
