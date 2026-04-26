import secrets
import string

from tortoise import fields

from .base import BaseModel, TimestampMixin


def generate_api_key():
    """生成 API Key: af_{32位随机字符串}"""
    random_str = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    return f"af_{random_str}"


class AppManagement(BaseModel, TimestampMixin):
    """应用管理表"""
    app_name = fields.CharField(max_length=64, default="", description="应用名称(英文)", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    api_key = fields.CharField(max_length=64, default=generate_api_key, description="API密钥", unique=True)
    dify_url = fields.CharField(max_length=255, default="", description="Dify服务地址")
    dify_api_key = fields.CharField(max_length=128, default="", description="Dify API密钥")
    description = fields.CharField(max_length=255, null=True, description="应用描述")
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
    template_content = fields.TextField(null=True, description="模板内容")

    class Meta:
        table = "summary_template"


class DropdownOption(BaseModel, TimestampMixin):
    """下拉选项类填单模板表"""
    summary = fields.CharField(max_length=500, default="", description="字段摘要")
    description = fields.TextField(null=True, description="详细说明")
    class_name = fields.CharField(max_length=64, default="", description="模板分类", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    app_name = fields.CharField(max_length=64, default="", description="应用名称", index=True)
    parent_id = fields.BigIntField(default=0, description="父选项ID，0表示顶级选项", index=True)
    option_value = fields.CharField(max_length=128, default="", description="选项值", index=True)

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
    data = fields.JSONField(null=True, description="填单数据")
    # AI填单相关字段
    status = fields.CharField(max_length=32, default="pending", description="处理状态: pending/queued/processing/completed/failed/timeout", index=True)
    result = fields.JSONField(null=True, description="AI填单结果数据")
    error_msg = fields.TextField(null=True, description="错误信息")
    processed_at = fields.DatetimeField(null=True, description="处理完成时间")

    class Meta:
        table = "fill_data_record"
