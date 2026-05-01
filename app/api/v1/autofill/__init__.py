from .autofill import app_router, dropdown_router, record_router, template_router
from .fill_page import field_group_router, field_spec_router, page_router

__all__ = [
    "app_router",
    "template_router",
    "dropdown_router",
    "record_router",
    "page_router",
    "field_group_router",
    "field_spec_router",
]
