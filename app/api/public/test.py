"""
测试路由 - 用于验证日志记录
"""
from fastapi import APIRouter

router = APIRouter()


@router.post("/test/error", include_in_schema=False)
async def test_error():
    """测试错误日志 - 触发异常"""
    def inner_function():
        def deepest_function():
            raise ValueError("测试异常：验证日志调用栈记录")
        deepest_function()
    
    inner_function()


@router.post("/test/success", include_in_schema=False)
async def test_success():
    """测试成功响应"""
    return {"code": 0, "msg": "success", "data": {"message": "测试成功响应", "nested": {"key": "value"}}}
