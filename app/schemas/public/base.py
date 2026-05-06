"""
Public API 基础请求模型
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BasePublicRequest(BaseModel):
    """公开接口基础请求类"""
    page_name: str = Field(..., description="页面名称（必填）")
    
    class Config:
        extra = "allow"  # 允许额外字段
