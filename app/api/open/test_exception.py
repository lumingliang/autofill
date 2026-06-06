"""
测试异常处理的路由
用于验证全局异常捕获和日志记录
"""
from fastapi import APIRouter

from app.core.exceptions import (
    BusinessException,
    PermissionDeniedException,
    ResourceNotFoundException,
    ValidationException,
)

router = APIRouter()


@router.post("/test/exception/business", include_in_schema=False)
async def test_business_exception():
    """测试业务异常"""
    raise BusinessException(code=400, msg="业务逻辑错误", data={"detail": "自定义业务错误"})


@router.post("/test/exception/permission", include_in_schema=False)
async def test_permission_exception():
    """测试权限异常"""
    raise PermissionDeniedException("您没有权限访问此资源")


@router.post("/test/exception/not-found", include_in_schema=False)
async def test_not_found_exception():
    """测试资源不存在异常"""
    raise ResourceNotFoundException("请求的资源不存在")


@router.post("/test/exception/validation", include_in_schema=False)
async def test_validation_exception():
    """测试验证异常"""
    raise ValidationException("数据验证失败")


@router.post("/test/exception/unexpected", include_in_schema=False)
async def test_unexpected_exception():
    """测试未预期异常（被全局捕获）"""
    def inner():
        def deeper():
            raise ValueError("这是一个未预期的错误，用于测试全局异常捕获")
        deeper()
    inner()


@router.post("/test/exception/success", include_in_schema=False)
async def test_success():
    """测试正常响应"""
    return {"code": 0, "msg": "success", "data": {"test": "正常响应"}}
