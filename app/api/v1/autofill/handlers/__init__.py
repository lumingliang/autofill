"""
Autofill handlers package
"""
from .page_handlers import router as page_router
from .field_group_handlers import router as field_group_router
from .field_spec_handlers import router as field_spec_router
from .app_handlers import router as app_router
from .template_handlers import router as template_router
from .dropdown_handlers import router as dropdown_router
from .record_handlers import router as record_router

__all__ = [
    "page_router",
    "field_group_router",
    "field_spec_router",
    "app_router",
    "template_router",
    "dropdown_router",
    "record_router",
]
