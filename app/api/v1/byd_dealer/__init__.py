"""
比亚迪经销商门店内部 API (JWT 认证)

本模块提供比亚迪经销商门店的内部管理接口，使用 JWT 认证，
主要供管理后台使用，包含完整的 CRUD 操作。
"""
from fastapi import APIRouter

from .byd_dealer import byd_dealer_router

__all__ = ["byd_dealer_router"]
