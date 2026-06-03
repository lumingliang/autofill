"""
批量测试模块相关 Schemas
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== 查询参数 ====================

class BatchTestListQuery(BaseModel):
    """批量测试任务列表查询参数"""
    page: int = Field(1, description="页码", ge=1)
    page_size: int = Field(10, description="每页数量", ge=1, le=100)
    keyword: str = Field("", description="关键词搜索（任务名称）")


class BatchTestResultQuery(BaseModel):
    """批量测试结果查询参数"""
    page: int = Field(1, description="页码", ge=1)
    page_size: int = Field(20, description="每页数量", ge=1, le=100)
    status: Optional[int] = Field(None, description="状态筛选：0-待执行, 1-执行中, 2-成功, 3-失败")


# ==================== 请求参数 ====================

class BatchTestImportRequest(BaseModel):
    """导入文件创建任务请求"""
    dify_agent_id: int = Field(..., description="Dify Agent ID", gt=0)
    task_name: Optional[str] = Field(None, description="任务名称（可选，默认使用文件名）", max_length=200)
    remark: str = Field("", description="备注", max_length=1000)


class BatchTestRetryRequest(BaseModel):
    """重新执行任务请求"""
    task_id: int = Field(..., description="任务ID", gt=0)


# ==================== 响应数据 ====================

class BatchTestTaskOut(BaseModel):
    """批量测试任务输出"""
    id: int
    task_name: str = ""
    version_no: int = 1
    dify_agent_id: int = 0
    dify_agent_name: str = ""
    file_name: str = ""
    file_size: int = 0
    row_count: int = 0
    collection_name: str = ""
    status: int = 0
    success_count: int = 0
    fail_count: int = 0
    remark: str = ""
    created_by: int = 0
    created_at: str = ""
    updated_at: str = ""

    class Config:
        from_attributes = True


class BatchTestTaskDetailOut(BaseModel):
    """批量测试任务详情输出"""
    id: int
    task_name: str = ""
    version_no: int = 1
    dify_agent_id: int = 0
    dify_agent_name: str = ""
    file_name: str = ""
    file_size: int = 0
    row_count: int = 0
    collection_name: str = ""
    status: int = 0
    success_count: int = 0
    fail_count: int = 0
    remark: str = ""
    created_by: int = 0
    created_by_name: str = ""
    created_at: str = ""
    updated_at: str = ""

    class Config:
        from_attributes = True


class BatchTestImportResponse(BaseModel):
    """导入任务响应"""
    task_id: int
    task_name: str
    version_no: int
    row_count: int
    status: int
    collection_name: str


class BatchTestRetryResponse(BaseModel):
    """重新执行响应"""
    task_id: int
    version_no: int
    collection_name: str
    status: int


class BatchTestStopResponse(BaseModel):
    """停止任务响应"""
    task_id: int
    status: int
    message: str


class BatchTestFilePreview(BaseModel):
    """文件预览响应"""
    file_name: str
    file_size: int
    row_count: int
    headers: List[str]
    sample_data: List[Dict[str, str]]
    has_query_column: bool


class BatchTestResultItem(BaseModel):
    """测试结果项"""
    id: str
    row_index: int
    query: str
    status: int
    execution_time_ms: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_msg: str = ""

    class Config:
        extra = "allow"  # 允许动态字段（Dify 返回的字段）


class BatchTestResultList(BaseModel):
    """测试结果列表"""
    total: int
    items: List[Dict[str, Any]]
