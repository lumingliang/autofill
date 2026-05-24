"""
规则管理模块数据模型
"""
from tortoise import fields

from .base import BaseModel


class RuleInfo(BaseModel):
    """规则信息表"""
    tenant_id = fields.BigIntField(default=0, index=True, description="租户ID")
    app_name = fields.CharField(max_length=64, default="", index=True, description="应用名称")
    rule_code = fields.CharField(max_length=64, index=True, description="规则唯一编码")
    rule_name = fields.CharField(max_length=128, description="规则名称")
    desc = fields.CharField(max_length=512, default="", description="规则描述")
    latest_version_id = fields.BigIntField(null=True, description="最新版本ID")
    config = fields.TextField(null=True, description="CSV导入配置（JSON格式）")
    curl_config = fields.TextField(null=True, description="CURL导入配置（JSON格式）")
    status = fields.IntField(default=1, description="状态：0-禁用，1-启用")
    deleted = fields.IntField(default=0, index=True, description="是否删除：0-未删除，1-已删除")
    deleted_at = fields.DatetimeField(null=True, description="删除时间")
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "rule_info"
        unique_together = (("tenant_id", "app_name", "rule_code"),)


class RuleVersion(BaseModel):
    """规则版本表"""
    tenant_id = fields.BigIntField(default=0, index=True, description="租户ID")
    app_name = fields.CharField(max_length=64, default="", index=True, description="应用名称")
    rule_id = fields.BigIntField(index=True, description="规则ID")
    version_no = fields.IntField(description="版本号，从1开始递增")
    content_md5 = fields.CharField(max_length=32, description="内容MD5，用于乐观锁")
    storage_type = fields.IntField(default=1, description="存储类型：1-数据库，2-文件系统")
    content_json = fields.TextField(null=True, description="规则内容JSON格式（CSV数据转JSON），小文件(<1MB)存储在此")
    file_path = fields.CharField(max_length=512, default="", description="CSV文件存储路径，大文件(≥1MB)存储在文件系统")
    file_size = fields.BigIntField(default=0, description="文件大小（字节）")
    remark = fields.CharField(max_length=512, default="", description="版本备注，记录本次修改内容")
    status = fields.IntField(default=1, description="状态：0-废弃，1-有效")
    deleted = fields.IntField(default=0, index=True, description="是否删除：0-未删除，1-已删除")
    created_at = fields.DatetimeField(auto_now_add=True, index=True)

    class Meta:
        table = "rule_version"
