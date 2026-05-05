"""
Autofill v1 API 路由
"""
from app.api.v1.autofill.handlers import (
    app_router,
    dropdown_router,
    record_router,
    template_router,
)

# 导出路由
app_router = app_router
template_router = template_router
dropdown_router = dropdown_router
record_router = record_router
