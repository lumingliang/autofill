from typing import Any, Dict, List

from pydantic import BaseModel, Field


# ==================== 填单页面 Schemas ====================

class FillPageCreate(BaseModel):
    page_name: str = Field(..., max_length=64)
    page_code: str = Field("", max_length=64, pattern=r"^[a-zA-Z0-9_]*$", description="页面编码，不传则后端自动生成")
    app_name: str = Field(..., max_length=64, description="关联应用名称")
    app_id: int = Field(0, description="关联应用ID，后端自动填充")
    tenant_id: int = Field(0, description="租户ID")
    description: str = Field("", description="页面描述")
    dify_agent_url: str = Field("", max_length=512, description="Dify Agent URL")
    dify_api_key: str = Field("", max_length=128, description="Dify API Key")
    is_active: bool = Field(True, description="是否启用")


class FillPageUpdate(BaseModel):
    id: int
    page_name: str = Field("", max_length=64)
    page_code: str = Field("", max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    app_name: str = Field("", max_length=64, description="关联应用名称")
    app_id: int = Field(0, description="关联应用ID，后端自动填充")
    description: str = Field("", description="页面描述")
    dify_agent_url: str = Field("", max_length=512, description="Dify Agent URL")
    dify_api_key: str = Field("", max_length=128, description="Dify API Key")
    is_active: bool = Field(True, description="是否启用")


class FillPageOut(BaseModel):
    id: int
    page_name: str = ""
    page_code: str = ""
    app_id: int = 0
    app_name: str = ""
    tenant_id: int = 0
    description: str = ""
    dify_agent_url: str = ""
    dify_api_key: str = ""
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""

    class Config:
        from_attributes = True


# ==================== 字段组配置 Schemas ====================

class OutputTemplateItem(BaseModel):
    """输出模板项"""
    template: str = ""
    description: str = ""


class FieldGroupConfigCreate(BaseModel):
    group_name: str = Field(..., max_length=64)
    group_code: str = Field("", max_length=64, pattern=r"^[a-zA-Z0-9_]*$", description="字段组编码，不传则后端自动生成")
    page_id: int = Field(0, description="关联页面ID")
    app_name: str = Field("", max_length=64)
    page_name: str = Field("", max_length=64)
    prompt_template_base: str = Field("", description="Prompt基础模板")
    output_templates: Dict[str, OutputTemplateItem] = Field(default_factory=dict)
    description: str = Field("", description="字段组描述")
    tenant_id: int = Field(0, description="租户ID")
    is_active: bool = Field(True, description="是否启用")


class FieldGroupConfigUpdate(BaseModel):
    id: int
    group_name: str = Field("", max_length=64)
    group_code: str = Field("", max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    page_id: int = Field(0, description="关联页面ID")
    app_name: str = Field("", max_length=64)
    page_name: str = Field("", max_length=64)
    prompt_template_base: str = Field("", description="Prompt基础模板")
    output_templates: Dict[str, OutputTemplateItem] = Field(default_factory=dict)
    description: str = Field("", description="字段组描述")
    is_active: bool = Field(True, description="是否启用")


class FieldGroupConfigOut(BaseModel):
    id: int
    group_name: str = ""
    group_code: str = ""
    app_name: str = ""
    page_id: int = 0
    page_name: str = ""
    prompt_template_base: str = ""
    output_templates: Dict = {}
    description: str = ""
    tenant_id: int = 0
    is_active: bool = True
    version: int = 0
    created_at: str = ""
    updated_at: str = ""

    class Config:
        from_attributes = True


# ==================== 字段明细 Schemas ====================

class OptionItem(BaseModel):
    """选项项"""
    value: str = ""
    label: str = ""
    fill_instruction: str = Field(default="", description="选项填写指引/说明")
    corrections: List[Dict] = []
    is_deleted: bool = False


class FieldOptions(BaseModel):
    """字段选项配置（select类型）"""
    source: str = Field(default="static", description="选项来源：static/api")
    api_identifier: str = Field("", description="API标识")
    last_sync_at: str = Field("", description="最后同步时间")
    items: List[OptionItem] = []
    swagger_json: str = Field("", description="OpenAI Swagger JSON 文档")
    appkey: str = Field("", description="API 调用鉴权密钥")
    # 选择模式和数量限制（selection_mode: 0=单选, 1=多选）
    selection_mode: int = Field(default=0, description="选择模式：0=单选(默认), 1=多选")
    min_selections: int = Field(default=1, description="最少选择数量（多选时有效）")
    max_selections: int = Field(default=1, description="最多选择数量（多选时有效，0表示无限制）")


class FieldSpecCreate(BaseModel):
    field_name: str = Field(..., max_length=64)
    field_label: str = Field("", max_length=128)
    field_type: str = Field(default="text")
    tenant_id: int = Field(0, description="租户ID")
    app_name: str = Field("", max_length=64, description="应用名称")
    fill_instruction: str = Field("", description="字段填写指引")
    options: FieldOptions = Field(default_factory=FieldOptions)
    corrections: List[Dict] = []
    is_active: bool = Field(True, description="是否启用")
    field_group_ids: List[int] = Field(default_factory=list, description="关联字段组ID列表")


class FieldSpecUpdate(BaseModel):
    id: int
    field_name: str = Field("", max_length=64)
    field_label: str = Field("", max_length=128)
    field_type: str = Field("", description="字段类型")
    tenant_id: int = Field(0, description="租户ID")
    app_name: str = Field("", max_length=64, description="应用名称")
    fill_instruction: str = Field("", description="字段填写指引")
    options: FieldOptions = Field(default_factory=FieldOptions)
    corrections: List[Dict] = []
    is_active: bool = Field(True, description="是否启用")
    field_group_ids: List[int] = Field(default_factory=list, description="关联字段组ID列表")


class FieldSpecOut(BaseModel):
    id: int
    field_name: str = ""
    field_label: str = ""
    field_type: str = ""
    tenant_id: int = 0
    app_name: str = ""
    fill_instruction: str = ""
    options: FieldOptions = Field(default_factory=FieldOptions)
    corrections: List[Dict] = []
    is_active: bool = True
    field_group_ids: List[int] = []
    field_groups: List[Dict] = []
    created_at: str = ""
    updated_at: str = ""

    class Config:
        from_attributes = True


# ==================== 公开接口请求 Schemas ====================

class FieldGroupQueryRequest(BaseModel):
    app_name: str = Field("", description="应用名称")
    page_name: str = Field("", description="页面名称")
    field_group_name: str = Field("", description="字段组名称")
    code: str = Field("", description="字段组编码")


class FieldSpecListRequest(BaseModel):
    field_group_id: int = Field(0, description="字段组ID")


class FieldSpecQueryRequest(BaseModel):
    field_group_id: int = Field(0, description="字段组ID")
    field_name: str = Field("", description="字段名称")
    field_type: str = Field("", description="字段类型")


# ==================== Swagger 同步接口 Schemas ====================

class SwaggerSyncRequest(BaseModel):
    """Swagger 同步请求"""
    field_spec_id: int = Field(..., description="字段明细ID")
    swagger_json: str = Field(..., description="OpenAI Swagger JSON 文档")
    appkey: str = Field("", description="API 调用鉴权密钥")


class SwaggerSyncResponse(BaseModel):
    """Swagger 同步响应"""
    success: bool = Field(False, description="是否同步成功")
    message: str = Field("", description="同步结果消息")
    synced_count: int = Field(0, description="同步的选项数量")
    endpoints: List[Dict] = Field(default_factory=list, description="解析的API端点列表")
