"""
填单页面管理接口
"""
from app.api.v1.autofill.handlers import (
    field_group_router,
    field_spec_router,
    cascade_router,
)

# 导出路由
field_group_router = field_group_router
field_spec_router = field_spec_router
cascade_router = cascade_router
