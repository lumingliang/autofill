from .autofill import app_router, record_router, test_fill_router, rule_router, rule_test_router, rule_import_router, system_prompt_router
from .fill_page import field_group_router, field_spec_router

__all__ = [
    "app_router",
    "record_router",
    "field_group_router",
    "field_spec_router",
    "test_fill_router",
    "rule_router",
    "rule_test_router",
    "rule_import_router",
    "system_prompt_router",
]
