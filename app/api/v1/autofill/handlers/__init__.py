"""
Autofill handlers package
"""
from .app_handlers import router as app_router
from .record_handlers import router as record_router
from .rule_handlers import router as rule_router
from .rule_test_handlers import router as rule_test_router
from .rule_import_handlers import router as rule_import_router
from .system_prompt_handlers import router as system_prompt_router

__all__ = [
    "app_router",
    "record_router",
    "rule_router",
    "rule_test_router",
    "rule_import_router",
    "system_prompt_router",
]
