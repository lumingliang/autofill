from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== 字段组配置 Schemas（删除页面关联） ====================

class OutputTemplateItem(BaseModel):
    """输出模板项"""
    template: str = ""
    description: str = ""


class FieldGroupConfigCreate(BaseModel):
    group_name: str = Field(..., max_length=64)
    group_code: str = Field("", max_length=64, pattern=r"^[a-zA-Z0-9_]*$", description="字段组编码，不传则后端自动生成")
    app_name: str = Field(..., max_length=64, description="关联应用名称")
    prompt_template_base: str = Field("", description="Prompt基础模板")
    output_templates: Dict[str, OutputTemplateItem] = Field(default_factory=dict)
    description: str = Field("", description="字段组描述")
    tenant_id: int = Field(0, description="租户ID")
    is_active: bool = Field(True, description="是否启用")


class FieldGroupConfigUpdate(BaseModel):
    id: int
    group_name: str = Field("", max_length=64)
    group_code: str = Field("", max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    app_name: str = Field("", max_length=64, description="关联应用名称")
    prompt_template_base: str = Field("", description="Prompt基础模板")
    output_templates: Dict[str, OutputTemplateItem] = Field(default_factory=dict)
    description: str = Field("", description="字段组描述")
    is_active: bool = Field(True, description="是否启用")


class FieldGroupConfigOut(BaseModel):
    id: int
    group_name: str = ""
    group_code: str = ""
    app_name: str = ""
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
    is_deleted: bool = False


class FieldOptions(BaseModel):
    """字段选项配置（下拉单选/多选类型）"""
    items: List[OptionItem] = []
    # 数量限制（仅多选时有效）
    min_selections: int = Field(default=1, description="最少选择数量（多选时有效）")
    max_selections: int = Field(default=0, description="最多选择数量（多选时有效，0表示无限制）")


class FieldSpecCreate(BaseModel):
    field_name: str = Field(..., max_length=64)
    field_label: str = Field("", max_length=128)
    field_type: str = Field(default="text")
    tenant_id: int = Field(0, description="租户ID")
    app_name: str = Field(..., max_length=64, description="应用名称")
    field_group_id: int = Field(0, description="关联字段组ID，可选")
    fill_instruction: str = Field("", description="字段填写指引")
    options: FieldOptions = Field(default_factory=FieldOptions)
    is_active: bool = Field(True, description="是否启用")


class FieldSpecUpdate(BaseModel):
    id: int
    field_name: str = Field("", max_length=64)
    field_label: str = Field("", max_length=128)
    field_type: str = Field("", description="字段类型")
    tenant_id: int = Field(0, description="租户ID")
    app_name: str = Field("", max_length=64, description="应用名称")
    field_group_id: int = Field(0, description="关联字段组ID，可选")
    fill_instruction: str = Field("", description="字段填写指引")
    options: FieldOptions = Field(default_factory=FieldOptions)
    is_active: bool = Field(True, description="是否启用")


class FieldSpecOut(BaseModel):
    id: int
    field_name: str = ""
    field_label: str = ""
    field_type: str = ""
    tenant_id: int = 0
    app_name: str = ""
    fill_instruction: str = ""
    options: FieldOptions = Field(default_factory=FieldOptions)
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""

    class Config:
        from_attributes = True


# ==================== 公开接口请求 Schemas ====================

class FieldGroupQueryRequest(BaseModel):
    app_name: str = Field("", description="应用名称")
    group_name: str = Field("", description="字段组名称")
    code: str = Field("", description="字段组编码")


class FieldGroupBatchAddFieldsRequest(BaseModel):
    """批量添加字段到字段组请求"""
    field_group_id: int = Field(..., description="字段组ID")
    field_spec_ids: List[int] = Field(..., description="字段ID列表")


class FieldGroupBatchAddFieldsResponse(BaseModel):
    """批量添加字段到字段组响应"""
    success_count: int = Field(default=0, description="成功添加数量")
    failed_count: int = Field(default=0, description="失败数量")
    message: str = Field(default="", description="操作结果消息")


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
