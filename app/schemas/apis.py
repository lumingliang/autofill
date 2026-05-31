from pydantic import BaseModel, Field

from app.models.enums import MethodType


class ApiListQuery(BaseModel):
    """API列表查询参数"""
    page: int = Field(1, description="页码")
    page_size: int = Field(10, description="每页数量")
    path: str = Field("", description="API路径")
    summary: str = Field("", description="API简介")
    tags: str = Field("", description="API标签")
    api_code: str = Field("", description="API编码")


class BaseApi(BaseModel):
    api_code: str = Field(..., description="API唯一编码", example="user:list")
    path: str = Field(..., description="API路径", example="/api/v1/user/list")
    summary: str = Field("", description="API简介", example="查看用户列表")
    method: MethodType = Field(..., description="API方法", example="GET")
    tags: str = Field("", description="API标签", example="User")


class ApiCreate(BaseApi): ...


class ApiUpdate(BaseApi):
    id: int
