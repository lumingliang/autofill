from fastapi import Query
from pydantic import BaseModel, Field


class BaseDept(BaseModel):
    name: str = Field(..., description="部门名称", example="研发中心")
    desc: str = Field("", description="备注", example="研发中心")
    order: int = Field(0, description="排序")
    parent_id: int = Field(0, description="父部门ID")


class DeptListQuery(BaseModel):
    """部门列表查询参数"""
    name: str = Query("", description="部门名称")
    tenant_id: int = Query(0, description="租户ID（仅超级管理员可用）")


class DeptGetQuery(BaseModel):
    """部门获取参数"""
    id: int = Query(..., description="部门ID")


class DeptCreate(BaseDept):
    # 多租户字段：部门所属租户ID（仅超级管理员可设置）
    tenant_id: int = Field(0, description="租户ID")


class DeptUpdate(BaseDept):
    id: int
    # 多租户字段：部门所属租户ID（仅超级管理员可设置）
    tenant_id: int = Field(0, description="租户ID")

    def update_dict(self):
        return self.model_dump(exclude_unset=True, exclude={"id"})


class DeptDeleteQuery(BaseModel):
    """部门删除参数"""
    dept_id: int = Query(..., description="部门ID")
