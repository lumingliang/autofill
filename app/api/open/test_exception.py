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


@router.post("/test/exception/name-error", include_in_schema=False)
async def test_name_error():
    """测试 NameError - 引用不存在的变量（故意的运行时错误）"""
    # 故意引用一个不存在的变量
    return non_existent_variable  # noqa: F821


@router.post("/test/exception/key-error", include_in_schema=False)
async def test_key_error():
    """测试 KeyError - 访问字典不存在的键（故意的运行时错误）"""
    data = {"name": "test"}
    # 故意访问不存在的键
    return data["non_existent_key"]


@router.post("/test/exception/index-error", include_in_schema=False)
async def test_index_error():
    """测试 IndexError - 列表越界（故意的运行时错误）"""
    items = [1, 2, 3]
    # 故意访问越界索引
    return items[100]


@router.post("/test/exception/type-error", include_in_schema=False)
async def test_type_error():
    """测试 TypeError - 类型错误（故意的运行时错误）"""
    # 故意进行不支持的类型操作
    return "string" + 123  # noqa: F821


@router.post("/test/exception/attribute-error", include_in_schema=False)
async def test_attribute_error():
    """测试 AttributeError - 访问不存在的属性（故意的运行时错误）"""
    text = "hello"
    # 故意访问字符串不存在的方法
    return text.non_existent_method()  # noqa: F821
