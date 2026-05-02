"""
比亚迪经销商门店 Schema
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class BYDDealerBase(BaseModel):
    """门店基础信息"""
    name: str = Field(..., description="门店名称")
    code: str = Field(..., description="门店编码")
    province: str = Field(..., description="省份")
    city: str = Field(..., description="城市")
    district: Optional[str] = Field(None, description="区县")
    address: str = Field(..., description="详细地址")
    phone: Optional[str] = Field(None, description="联系电话")
    contact_person: Optional[str] = Field(None, description="联系人")
    longitude: Optional[float] = Field(None, description="经度")
    latitude: Optional[float] = Field(None, description="纬度")
    dealer_type: str = Field(default="4S店", description="门店类型")
    status: str = Field(default="营业中", description="经营状态")
    service_types: List[str] = Field(default_factory=list, description="服务类型")
    business_hours: Optional[str] = Field(None, description="营业时间")
    brands: List[str] = Field(default_factory=lambda: ["比亚迪"], description="经营品牌")
    remark: Optional[str] = Field(None, description="备注")


class BYDDealerCreate(BYDDealerBase):
    """创建门店"""
    pass


class BYDDealerUpdate(BaseModel):
    """更新门店"""
    name: Optional[str] = Field(None, description="门店名称")
    code: Optional[str] = Field(None, description="门店编码")
    province: Optional[str] = Field(None, description="省份")
    city: Optional[str] = Field(None, description="城市")
    district: Optional[str] = Field(None, description="区县")
    address: Optional[str] = Field(None, description="详细地址")
    phone: Optional[str] = Field(None, description="联系电话")
    contact_person: Optional[str] = Field(None, description="联系人")
    longitude: Optional[float] = Field(None, description="经度")
    latitude: Optional[float] = Field(None, description="纬度")
    dealer_type: Optional[str] = Field(None, description="门店类型")
    status: Optional[str] = Field(None, description="经营状态")
    service_types: Optional[List[str]] = Field(None, description="服务类型")
    business_hours: Optional[str] = Field(None, description="营业时间")
    brands: Optional[List[str]] = Field(None, description="经营品牌")
    remark: Optional[str] = Field(None, description="备注")


class BYDDealerResponse(BYDDealerBase):
    """门店响应"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BYDDealerSearchParams(BaseModel):
    """门店搜索参数"""
    keyword: Optional[str] = Field(None, description="关键词(门店名称/地址)")
    city: Optional[str] = Field(None, description="城市")
    district: Optional[str] = Field(None, description="区县")
    dealer_type: Optional[str] = Field(None, description="门店类型")
    status: Optional[str] = Field(None, description="经营状态")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class BYDDealerSearchResponse(BaseModel):
    """门店搜索响应"""
    total: int = Field(..., description="总数")
    items: List[BYDDealerResponse] = Field(..., description="门店列表")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")


class BYDDealerPublicSearchRequest(BaseModel):
    """公开接口搜索请求"""
    app_key: str = Field(..., description="AppKey")
    query: str = Field(..., description="查询内容(支持自然语言)")
    city: Optional[str] = Field(None, description="城市过滤")
    limit: int = Field(default=10, ge=1, le=50, description="返回数量限制")


class BYDDealerPublicSearchResponse(BaseModel):
    """公开接口搜索响应"""
    success: bool = Field(..., description="是否成功")
    data: List[BYDDealerResponse] = Field(default_factory=list, description="门店列表")
    total: int = Field(default=0, description="匹配总数")
    query: str = Field(..., description="原始查询")
    matched_keywords: List[str] = Field(default_factory=list, description="匹配到的关键词")
    message: Optional[str] = Field(None, description="提示信息")


class ChatRecordDealerQuery(BaseModel):
    """聊天记录门店查询"""
    app_key: str = Field(..., description="AppKey")
    chat_history: str = Field(..., description="聊天记录文本")
    limit: int = Field(default=5, ge=1, le=20, description="返回数量限制")
