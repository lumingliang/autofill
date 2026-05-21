"""
Autofill handlers package
"""
from .field_group_handlers import router as field_group_router
from .field_spec_handlers import router as field_spec_router
from .app_handlers import router as app_router
from .template_handlers import router as template_router
from .dropdown_handlers import router as dropdown_router
from .record_handlers import router as record_router
from .test_fill_handlers import router as test_fill_router
from .cascade_handlers import router as cascade_router

__all__ = [
    "field_group_router",
    "field_spec_router",
    "app_router",
    "template_router",
    "dropdown_router",
    "record_router",
    "test_fill_router",
    "cascade_router",
]
