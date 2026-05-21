import secrets
import string
from enum import Enum

from tortoise import fields

from .base import BaseModel, TimestampMixin


def generate_api_key():
    """生成 API Key: af_{32位随机字符串}"""
    random_str = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    return f"af_{random_str}"


def generate_field_group_code():
    """生成字段组唯一标识: fg_{16位随机字符串}"""
    random_str = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(16))
    return f"fg_{random_str}"


class AppManagement(BaseModel, TimestampMixin):
    """应用管理表"""
    app_name = fields.CharField(max_length=64, default="", description="应用名称(英文)", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    api_key = fields.CharField(max_length=64, default=generate_api_key, description="API密钥", unique=True)
    dify_url = fields.CharField(max_length=255, default="", description="Dify服务地址")
    dify_api_key = fields.CharField(max_length=128, default="", description="Dify API密钥")
    description = fields.CharField(max_length=255, default="", description="应用描述")
    is_active = fields.BooleanField(default=True, description="是否启用", index=True)

    class Meta:
        table = "app_management"


class SummaryTemplate(BaseModel, TimestampMixin):
    """总结类填单模板表"""
    name = fields.CharField(max_length=128, default="", description="模板名称", index=True)
    app_name = fields.CharField(max_length=64, default="", description="应用名称", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    class_name = fields.CharField(max_length=64, default="", description="模板分类", index=True)
    summary = fields.CharField(max_length=500, default="", description="模板摘要")
    template_content = fields.TextField(default="", description="模板内容")

    class Meta:
        table = "summary_template"


class DropdownOption(BaseModel, TimestampMixin):
    """下拉选项类填单模板表"""
    summary = fields.CharField(max_length=500, default="", description="显示标签（下拉框中显示的文本）")
    description = fields.TextField(default="", description="选项说明（帮助提示信息）")
    class_name = fields.CharField(max_length=64, default="", description="模板分类", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    app_name = fields.CharField(max_length=64, default="", description="应用名称", index=True)
    parent_id = fields.BigIntField(default=0, description="父选项ID，0表示顶级选项", index=True)
    option_value = fields.CharField(max_length=128, default="", description="选项编码（唯一标识，如 EVT001）", index=True)

    class Meta:
        table = "dropdown_option"


class FillDataRecord(BaseModel, TimestampMixin):
    """填单数据记录表"""
    session_id = fields.CharField(max_length=64, default="", description="会话ID", index=True)
    phone = fields.CharField(max_length=32, default="", description="手机号", index=True)
    user_unique_id = fields.CharField(max_length=64, default="", description="用户唯一标识", index=True)
    user_name = fields.CharField(max_length=64, default="", description="用户名称", index=True)
    app_name = fields.CharField(max_length=64, default="", description="应用名称", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    data = fields.JSONField(default=dict, description="填单数据")
    # AI填单相关字段
    status = fields.CharField(max_length=32, default="pending", description="处理状态: pending/queued/processing/completed/failed/timeout", index=True)
    result = fields.JSONField(default=dict, description="AI填单结果数据")
    error_msg = fields.TextField(default="", description="错误信息")
    processed_at = fields.DatetimeField(null=True, description="处理完成时间")

    class Meta:
        table = "fill_data_record"


# ==================== 字段类型枚举 ====================

class FieldType(str, Enum):
    """字段类型枚举 - 文本输入、下拉单选、下拉多选、模板类型"""
    TEXT = "text"           # 文本输入
    SELECT_SINGLE = "select_single"   # 下拉单选
    SELECT_MULTI = "select_multi"     # 下拉多选
    TEMPLATE = "template"   # 模板类型（新增）


# ==================== 字段组配置（删除页面关联） ====================

class FieldGroupConfig(BaseModel, TimestampMixin):
    """字段组配置表 - 直接关联应用，不再关联页面"""
    group_name = fields.CharField(max_length=64, default="", description="字段组名称", index=True)
    group_code = fields.CharField(max_length=64, description="字段组编码", unique=True, index=True, default=generate_field_group_code)
    app_name = fields.CharField(max_length=64, default="", description="应用名称", index=True)
    prompt_template_base = fields.TextField(default="", description="Prompt基础模板，包含{{fields_instructions}}占位符")
    output_templates = fields.JSONField(default=dict, description="多输出模板配置，如{key: {template, description}}")
    description = fields.TextField(default="", description="字段组描述")
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    is_active = fields.BooleanField(default=True, description="是否启用")
    version = fields.IntField(default=1, description="版本号，用于缓存控制")

    class Meta:
        table = "field_group_config"


class FieldSpec(BaseModel, TimestampMixin):
    """字段明细表 - 核心表（多对多关联字段组，通过中间表显式查询）"""
    field_name = fields.CharField(max_length=64, default="", description="字段英文名（用于JSON输出）")
    field_label = fields.CharField(default="", max_length=128, description="字段显示名称")
    field_type = fields.CharEnumField(FieldType, default=FieldType.TEXT, description="字段类型")
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    app_name = fields.CharField(max_length=64, default="", description="应用名称", index=True)
    fill_instruction = fields.TextField(default="", description="字段填写指引（用于生成LLM描述）")
    options = fields.JSONField(default=dict, description="select类型选项配置，含items/min_selections/max_selections")
    corrections = fields.JSONField(default=list, description="text类型全局批注列表[{id, text, created_by, created_at}]")
    is_active = fields.BooleanField(default=True, description="是否启用")

    class Meta:
        table = "field_spec"
        # 唯一索引：字段名 + 租户ID + 应用名称
        unique_together = (("field_name", "tenant_id", "app_name"),)


class FieldGroupFieldSpec(BaseModel, TimestampMixin):
    """字段组与字段关联中间表（多对多关系）"""
    field_group_id = fields.BigIntField(default=0, description="字段组ID", index=True)
    field_spec_id = fields.BigIntField(default=0, description="字段明细ID", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    app_name = fields.CharField(max_length=64, default="", description="应用名称", index=True)

    class Meta:
        table = "field_group_field_spec"


class FieldFlattenConfig(BaseModel, TimestampMixin):
    """字段展平配置 - 支持多级嵌套数据的展平"""
    field_spec_id = fields.BigIntField(default=0, description="关联字段ID", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    app_name = fields.CharField(max_length=64, default="", description="应用名称", index=True)
    
    # 标签展平配置
    label_path_level1 = fields.CharField(max_length=255, default="", description="第一级标签路径")
    label_path_level2 = fields.CharField(max_length=255, default="", description="第二级标签路径")
    label_path_level3 = fields.CharField(max_length=255, default="", description="第三级标签路径")
    label_separator = fields.CharField(max_length=16, default="-", description="标签拼接符")
    
    # 值展平配置
    value_path_level1 = fields.CharField(max_length=255, default="", description="第一级值路径")
    value_path_level2 = fields.CharField(max_length=255, default="", description="第二级值路径")
    value_path_level3 = fields.CharField(max_length=255, default="", description="第三级值路径")
    value_separator = fields.CharField(max_length=16, default="-", description="值拼接符")
    
    is_active = fields.BooleanField(default=True, description="是否启用")

    class Meta:
        table = "field_flatten_config"


class FieldCascadeConfig(BaseModel, TimestampMixin):
    """级联下拉配置 - 支持多级级联下拉"""
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    app_name = fields.CharField(max_length=64, default="", description="应用名称", index=True)
    
    # 父字段配置
    parent_field_id = fields.BigIntField(default=0, description="父字段ID", index=True)
    parent_field_name = fields.CharField(max_length=64, default="", description="父字段名称")
    parent_field_group_id = fields.BigIntField(default=0, description="父字段组ID", index=True)
    
    # 级联字段配置
    field_name_pattern = fields.CharField(max_length=255, default="parent.$.data[*].label + -的二三级", description="字段名规则")
    field_label_pattern = fields.CharField(max_length=255, default="parent.$.data[*].value + -的二三级", description="字段标签规则")
    
    # 级联API配置
    api_method = fields.CharField(max_length=16, default="GET", description="请求方法")
    api_url = fields.CharField(max_length=512, default="", description="API地址")
    api_headers = fields.JSONField(default=list, description="请求头列表")
    api_schema = fields.TextField(default="", description="OpenAPI Schema (YAML格式)")
    
    # 展平配置（针对此级联API的返回数据）
    enable_flatten = fields.BooleanField(default=False, description="是否启用展平")
    flatten_config = fields.JSONField(default=dict, description="展平配置，结构同FieldFlattenConfig")
    
    # 状态
    is_active = fields.BooleanField(default=True, description="是否启用")
    last_sync_at = fields.DatetimeField(null=True, description="最后同步时间")

    class Meta:
        table = "field_cascade_config"


class FieldCascadeData(BaseModel, TimestampMixin):
    """级联下拉数据缓存表 - 存储级联后的字段数据"""
    cascade_config_id = fields.BigIntField(default=0, description="级联配置ID", index=True)
    parent_value = fields.CharField(max_length=255, default="", description="父选项值", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    app_name = fields.CharField(max_length=64, default="", description="应用名称", index=True)
    child_field_id = fields.BigIntField(default=0, description="生成的子字段ID")
    child_field_name = fields.CharField(max_length=128, default="", description="生成的子字段名称")
    child_options = fields.JSONField(default=list, description="子字段选项列表")
    sync_status = fields.CharField(max_length=32, default="pending", description="同步状态: pending/success/failed")
    error_msg = fields.TextField(default="", description="错误信息")

    class Meta:
        table = "field_cascade_data"


class FieldSpecSyncRecord(BaseModel, TimestampMixin):
    """字段同步记录表（用于模板类型字段的同步）"""
    field_spec_id = fields.BigIntField(default=0, description="字段ID", index=True)

    # 同步状态: pending/processing/completed/failed
    status = fields.CharField(max_length=32, default="pending", description="同步状态", index=True)

    # 同步结果统计
    total_count = fields.IntField(default=0, description="模板总数")
    success_count = fields.IntField(default=0, description="成功数")
    failed_count = fields.IntField(default=0, description="失败数")

    # 错误信息
    error_msg = fields.TextField(default="", description="错误信息")

    # 详细结果
    details = fields.JSONField(default=dict, description="同步详情")

    # 关联信息
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    app_name = fields.CharField(max_length=64, default="", description="应用名称", index=True)

    class Meta:
        table = "field_spec_sync_record"
