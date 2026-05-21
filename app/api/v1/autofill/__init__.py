from .autofill import app_router, dropdown_router, record_router, template_router, test_fill_router
from .fill_page import field_group_router, field_spec_router, cascade_router

__all__ = [
    "app_router",
    "template_router",
    "dropdown_router",
    "record_router",
    "field_group_router",
    "field_spec_router",
    "test_fill_router",
    "cascade_router",
]
