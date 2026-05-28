"""
Autofill v1 API 路由
"""
from app.api.v1.autofill.handlers import (
    app_router,
    record_router,
    test_fill_router,
    rule_router,
    rule_test_router,
    rule_import_router,
    system_prompt_router,
)

# 导出路由
app_router = app_router
record_router = record_router
test_fill_router = test_fill_router
rule_router = rule_router
rule_test_router = rule_test_router
rule_import_router = rule_import_router
system_prompt_router = system_prompt_router
