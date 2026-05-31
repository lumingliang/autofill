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
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "rule_info"
        unique_together = (("tenant_id", "app_name", "rule_code"),)


class RuleVersion(BaseModel):
    """规则版本表 - 使用 seekdb 存储 CSV 数据"""
    tenant_id = fields.BigIntField(default=0, index=True, description="租户ID")
    app_name = fields.CharField(max_length=64, default="", index=True, description="应用名称")
    rule_id = fields.BigIntField(index=True, description="规则ID")
    rule_code = fields.CharField(max_length=64, default="", description="规则编码")
    version_no = fields.IntField(description="版本号，从1开始递增")
    content_md5 = fields.CharField(max_length=32, description="内容MD5，用于乐观锁")
    seekdb_collection_name = fields.CharField(max_length=128, default="", description="seekdb 集合名称")
    doc_count = fields.BigIntField(default=0, description="CSV 数据行数")
    headers = fields.JSONField(null=True, description="CSV 表头列表（JSON格式）")
    remark = fields.CharField(max_length=512, default="", description="版本备注，记录本次修改内容")
    status = fields.IntField(default=1, description="状态：0-废弃，1-有效")
    created_at = fields.DatetimeField(auto_now_add=True, index=True)

    class Meta:
        table = "rule_version"
