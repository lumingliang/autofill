"""
Autofill handlers package
"""
from .field_group_handlers import router as field_group_router
from .field_spec_handlers import router as field_spec_router
from .app_handlers import router as app_router
from .record_handlers import router as record_router
from .test_fill_handlers import router as test_fill_router
from .rule_handlers import router as rule_router
from .rule_test_handlers import router as rule_test_router
from .rule_import_handlers import router as rule_import_router
from .system_prompt_handlers import router as system_prompt_router

__all__ = [
    "field_group_router",
    "field_spec_router",
    "app_router",
    "record_router",
    "test_fill_router",
    "rule_router",
    "rule_test_router",
    "rule_import_router",
    "system_prompt_router",
]
