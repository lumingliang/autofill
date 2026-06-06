"""
Open API 基础请求模型
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BaseOpenRequest(BaseModel):
    """开放接口基础请求类"""

    class Config:
        extra = "allow"  # 允许额外字段
