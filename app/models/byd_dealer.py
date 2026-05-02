"""
比亚迪经销商门店模型
"""
from tortoise import fields, models

from app.models.base import BaseModel, TimestampMixin


class BYDDealer(BaseModel, TimestampMixin):
    """比亚迪经销商门店"""

    # 关联信息
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    app_id = fields.BigIntField(default=0, description="应用ID", index=True)

    # 门店基本信息
    name = fields.CharField(max_length=200, description="门店名称")
    code = fields.CharField(max_length=50, unique=True, description="门店编码")

    # 地址信息
    province = fields.CharField(max_length=50, description="省份")
    city = fields.CharField(max_length=50, description="城市")
    district = fields.CharField(max_length=100, null=True, description="区县")
    address = fields.CharField(max_length=500, description="详细地址")

    # 联系信息
    phone = fields.CharField(max_length=50, null=True, description="联系电话")
    contact_person = fields.CharField(max_length=100, null=True, description="联系人")

    # 经纬度（用于地图定位）
    longitude = fields.FloatField(null=True, description="经度")
    latitude = fields.FloatField(null=True, description="纬度")

    # 门店类型
    dealer_type = fields.CharField(
        max_length=50,
        default="4S店",
        description="门店类型(4S店/城市展厅/体验中心等)"
    )

    # 经营状态
    status = fields.CharField(
        max_length=20,
        default="营业中",
        description="经营状态(营业中/装修中/暂停营业)"
    )

    # 服务能力
    service_types = fields.JSONField(
        default=list,
        description="服务类型(销售/售后/维修/充电等)"
    )

    # 营业时间
    business_hours = fields.CharField(
        max_length=200,
        null=True,
        description="营业时间"
    )

    # 品牌信息
    brands = fields.JSONField(
        default=lambda: ["比亚迪"],
        description="经营品牌"
    )

    # 备注
    remark = fields.TextField(null=True, description="备注")

    class Meta:
        table = "byd_dealers"
        table_description = "比亚迪经销商门店表"
        indexes = [
            ("tenant_id",),
            ("app_id",),
            ("city",),
            ("district",),
            ("name",),
            ("status",),
        ]

    def __str__(self):
        return f"{self.name}({self.city})"

    async def to_dict(self):
        """转换为字典"""
        data = await super().to_dict()
        return data


class BYDDealerSearchLog(BaseModel, TimestampMixin):
    """门店搜索日志"""

    query = fields.TextField(description="查询内容")
    app_key = fields.CharField(max_length=100, description="AppKey")
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    search_params = fields.JSONField(default=dict, description="搜索参数")
    result_count = fields.IntField(default=0, description="返回结果数")
    success = fields.BooleanField(default=True, description="是否成功")
    error_msg = fields.TextField(null=True, description="错误信息")
    response_time_ms = fields.IntField(null=True, description="响应时间(ms)")

    class Meta:
        table = "byd_dealer_search_logs"
        table_description = "门店搜索日志表"
