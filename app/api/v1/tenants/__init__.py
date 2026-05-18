from fastapi import APIRouter

from .tenants import router

tenant_router = APIRouter()
tenant_router.include_router(router, tags=["租户管理"])
