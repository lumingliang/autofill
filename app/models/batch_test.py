"""
批量测试模块数据模型

用于对 Dify Agent 进行批量测试，支持导入 Excel/CSV 文件，
选择 Dify Agent，系统自动执行测试并记录结果。
"""
from tortoise import fields

from .base import BaseModel, TimestampMixin


class BatchTestTask(BaseModel, TimestampMixin):
    """
    批量测试任务表

    存储每次导入的批量测试任务信息
    """
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    task_name = fields.CharField(max_length=200, description="任务名称", index=True)
    version_no = fields.IntField(default=1, description="版本号，从1开始，每次重新执行+1")
    dify_agent_id = fields.BigIntField(description="Dify Agent ID", index=True)
    file_name = fields.CharField(max_length=500, description="原始文件名")
    file_size = fields.IntField(default=0, description="文件大小(字节)")
    row_count = fields.IntField(default=0, description="数据行数")
    collection_name = fields.CharField(max_length=200, description="SeekDB集合名称（包含版本号）")
    status = fields.IntField(default=0, description="任务状态：0-待执行, 1-执行中, 2-已完成, 3-失败, 4-已停止")
    success_count = fields.IntField(default=0, description="成功数")
    fail_count = fields.IntField(default=0, description="失败数")
    remark = fields.CharField(max_length=1000, default="", description="备注")
    created_by = fields.BigIntField(default=0, description="创建人ID")

    class Meta:
        table = "batch_test_task"
