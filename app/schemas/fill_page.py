from typing import Any, Dict, List, Optional

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
    corrections: Any = Field(default=[], description="选项人工标注，可以是字符串或列表")
    is_deleted: bool = False


class ApiHeaderItem(BaseModel):
    """API请求Header配置项"""
    key: str = Field(default="", description="Header键")
    value: str = Field(default="", description="Header值")


class ApiParamItem(BaseModel):
    """API请求静态参数配置项"""
    key: str = Field(default="", description="参数键")
    value: str = Field(default="", description="参数值")


class FieldOptions(BaseModel):
    """字段选项配置（下拉单选/多选类型）"""
    items: List[OptionItem] = []
    # 数量限制（仅多选时有效）
    min_selections: int = Field(default=1, description="最少选择数量（多选时有效）")
    max_selections: int = Field(default=0, description="最多选择数量（多选时有效，0表示无限制）")
    # API配置
    api_headers: List[ApiHeaderItem] = Field(default_factory=list, description="API请求Header配置列表")
    api_params: List[ApiParamItem] = Field(default_factory=list, description="API请求静态参数配置列表（如app_name、class_name、parent_id等）")
    api_schema: str = Field(default="", description="OpenAPI/Swagger Schema配置（YAML格式）")
    # 模板解析提示词配置
    parse_prompt: str = Field(default="", description="自定义模板解析提示词（可选，留空使用默认提示词）")
    # 模板选择器配置
    enable_template_selector: bool = Field(default=False, description="是否启用模板选择器")
    template_selector_field_name: str = Field(default="template_selector", description="模板选择器字段名")
    template_selector_field_label: str = Field(default="模板选择", description="模板选择器字段标签")
    template_selector_label_path: str = Field(default="$.name", description="选项标签的JSONPath")
    template_selector_value_path: str = Field(default="$.id", description="选项值的JSONPath")


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


# ==================== 模板类型字段 Schemas ====================

class TemplateConfig(BaseModel):
    """模板类型配置"""
    curl_command: str = Field(..., description="CURL命令")
    template_name_path: str = Field(..., description="模板名称字段JSONPath")
    template_content_path: str = Field(..., description="模板内容字段JSONPath")
    group_name_pattern: str = Field(
        default="parent.$.data[*].template_name + 的服务记录",
        description="字段组名称生成规则"
    )
    parse_prompt: str = Field(
        default="",
        description="模板解析Prompt"
    )


class SyncTemplateFieldRequest(BaseModel):
    """同步模板类型字段请求"""
    field_spec_id: int = Field(..., description="字段ID")


class SyncTemplateFieldResponse(BaseModel):
    """同步模板类型字段响应"""
    sync_record_id: int = Field(..., description="同步记录ID")
    status: str = Field(..., description="同步状态")
    message: str = Field(..., description="提示信息")


class FieldSpecSyncStatusResponse(BaseModel):
    """字段同步状态查询响应"""
    sync_record_id: int
    field_spec_id: int
    status: str
    total_count: int
    success_count: int
    failed_count: int
    error_msg: str
    details: Dict
    created_at: str
    updated_at: str


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


class FieldSpecSyncOptionsRequest(BaseModel):
    """同步字段选项请求"""
    field_id: int = Field(0, description="字段ID（编辑时传入，新建时为0）")
    field_name: str = Field(..., description="字段名称（必填）")
    field_label: str = Field(..., description="字段标签（必填）")
    field_type: str = Field("select_single", description="字段类型")
    field_group_ids: List[int] = Field(default_factory=list, description="关联字段组ID列表（必填）")
    fill_instruction: str = Field("", description="填写指引")
    options: FieldOptions = Field(default_factory=FieldOptions, description="字段选项配置包含api_schema和api_headers")


class FieldSpecSyncOptionsResponse(BaseModel):
    """同步字段选项响应"""
    items: List[OptionItem] = Field(default_factory=list, description="同步后的选项列表")
    updated_count: int = Field(default=0, description="更新/插入的选项数量")
    message: str = Field(default="", description="同步结果消息")


class CurlParseRequest(BaseModel):
    """CURL 解析请求"""
    curl_command: str = Field(..., description="curl 命令字符串")
    label_path: Optional[str] = Field(None, description="标签字段的 JSONPath")
    value_path: Optional[str] = Field(None, description="值字段的 JSONPath")
    enable_flatten: bool = Field(False, description="是否启用展平")
    flatten_label_path_level1: Optional[str] = Field(None, description="标签路径1")
    flatten_label_path_level2: Optional[str] = Field(None, description="标签路径2")
    flatten_label_path_level3: Optional[str] = Field(None, description="标签路径3")
    flatten_label_separator: str = Field("-", description="标签拼接符")
    flatten_value_path_level1: Optional[str] = Field(None, description="值路径1")
    flatten_value_path_level2: Optional[str] = Field(None, description="值路径2")
    flatten_value_path_level3: Optional[str] = Field(None, description="值路径3")
    flatten_value_separator: str = Field("-", description="值拼接符")


class FlattenConfig(BaseModel):
    """展平配置"""
    label_path_level1: Optional[str] = Field(None, description="标签路径1")
    label_path_level2: Optional[str] = Field(None, description="标签路径2")
    label_path_level3: Optional[str] = Field(None, description="标签路径3")
    label_separator: str = Field("-", description="标签拼接符")
    value_path_level1: Optional[str] = Field(None, description="值路径1")
    value_path_level2: Optional[str] = Field(None, description="值路径2")
    value_path_level3: Optional[str] = Field(None, description="值路径3")
    value_separator: str = Field("-", description="值拼接符")


class ApplyFieldMappingRequest(BaseModel):
    """应用字段映射请求"""
    openapi_schema: str = Field(..., description="OpenAPI Schema YAML 字符串")
    label_path: str = Field("$.data[*].label", description="标签字段的 JSONPath")
    value_path: str = Field("$.data[*].value", description="值字段的 JSONPath")
    enable_flatten: bool = Field(False, description="是否启用展平")
    flatten_config: Optional[FlattenConfig] = Field(None, description="展平配置")


class CurlParseResponse(BaseModel):
    """CURL 解析响应"""
    openapi_schema: str = Field("", description="生成的 OpenAPI Schema (YAML 格式)")
    response_preview: Dict = Field(default_factory=dict, description="API 响应数据预览")
    message: str = Field("", description="处理结果消息")


# ==================== 模板类型 CURL 导入 Schemas ====================

class TemplateCurlParseRequest(BaseModel):
    """模板类型 CURL 解析请求"""
    curl_command: str = Field(..., description="curl 命令字符串")
    template_name_path: str = Field("$.data[*].name", description="模板名称字段的 JSONPath")
    template_content_path: str = Field("$.data[*].template_content", description="模板内容字段的 JSONPath")


class TemplateSelectorConfig(BaseModel):
    """模板选择器配置"""
    enabled: bool = Field(False, description="是否启用模板选择器")
    field_name: str = Field("template_selector", description="模板选择器字段名")
    field_label: str = Field("模板选择", description="模板选择器字段标签")
    label_path: str = Field("$.name", description="选项标签的 JSONPath")
    value_path: str = Field("$.id", description="选项值的 JSONPath")


class TemplateFieldMapping(BaseModel):
    """模板字段映射配置"""
    template_name_path: str = Field("$.data[*].name", description="模板名称字段的 JSONPath")
    template_content_path: str = Field("$.data[*].template_content", description="模板内容字段的 JSONPath")
    group_name_pattern: str = Field("{template_name} 服务记录", description="字段组名称生成规则，支持 {template_name} 占位符")
    parse_prompt: str = Field("", description="模板解析Prompt")
    template_selector: TemplateSelectorConfig = Field(default_factory=TemplateSelectorConfig, description="模板选择器配置")


class TemplateCurlApplyRequest(BaseModel):
    """模板类型 CURL 应用字段映射请求"""
    openapi_schema: str = Field(..., description="OpenAPI Schema YAML 字符串")
    field_mapping: TemplateFieldMapping = Field(..., description="字段映射配置")


class TemplateCurlParseResponse(BaseModel):
    """模板类型 CURL 解析响应"""
    openapi_schema: str = Field("", description="生成的 OpenAPI Schema (YAML 格式)")
    response_preview: Dict = Field(default_factory=dict, description="API 响应数据预览")
    message: str = Field("", description="处理结果消息")



