"""
Public API schemas
用于公开接口的请求/响应模型
"""
from .base import BasePublicRequest
from .field_group import (
    FieldGroupRequest,
    LLMFillRequest,
    OptimizeFieldInstructionRequest,
    StepLLMFillRequest,
    StepLLMFillResultRequest,
    ChatSessionRequest,
    TestFillRequest,
    StepLLMFillResponse,
    StepLLMFillResponseData,
)
from .schemas import (
    # 基础请求类
    BasePublicRequest as BaseRequest,
    PageBaseRequest,
    AppBaseRequest,
    TenantAppBaseRequest,
    # 字段明细相关
    FieldSpecListRequest,
    FieldSpecCreateRequest,
    FieldItem,
    UpsertFieldGroupRequest,
    # 字段组相关
    FieldGroupRequest,
    FieldGroupDetailRequest,
    # 填单数据相关
    RecordFillDataRequest,
    # 下拉选项相关
    DropdownOptionListRequest,
    DropdownOptionDetailRequest,
    FirstLevelMenusRequest,
    SubmenusTreeRequest,
    # 模板相关
    SummaryTemplateListRequest,
    SummaryTemplateDetailRequest,
    # LLM/AI填单相关
    AIFillDataRequest,
    AIFillDataResultRequest,
    LLMFillRequest,
    FieldGroupsSchemaRequest,
    OptimizeFieldInstructionRequest,
    # Agent相关
    AgentRunRequest,
    DataQueryRequest,
)

__all__ = [
    # 基础请求类
    "BasePublicRequest",
    "BaseRequest",
    "PageBaseRequest",
    "AppBaseRequest",
    "TenantAppBaseRequest",
    # 字段明细相关
    "FieldSpecListRequest",
    "FieldSpecCreateRequest",
    "FieldItem",
    "UpsertFieldGroupRequest",
    # 字段组相关
    "FieldGroupRequest",
    "FieldGroupDetailRequest",
    "LLMFillRequest",
    "OptimizeFieldInstructionRequest",
    "StepLLMFillRequest",
    "StepLLMFillResponse",
    "StepLLMFillResponseData",
    # 填单数据相关
    "RecordFillDataRequest",
    # 下拉选项相关
    "DropdownOptionListRequest",
    "DropdownOptionDetailRequest",
    "FirstLevelMenusRequest",
    "SubmenusTreeRequest",
    # 模板相关
    "SummaryTemplateListRequest",
    "SummaryTemplateDetailRequest",
    # LLM/AI填单相关
    "AIFillDataRequest",
    "AIFillDataResultRequest",
    "FieldGroupsSchemaRequest",
    # Agent相关
    "AgentRunRequest",
    "DataQueryRequest",
]
