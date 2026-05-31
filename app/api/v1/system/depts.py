from fastapi import APIRouter, Depends

from app.core.dependency import AuthControl
from app.models.admin import User
from app.schemas.base import Success
from app.schemas.depts import (
    DeptCreate,
    DeptDeleteQuery,
    DeptGetQuery,
    DeptListQuery,
    DeptUpdate,
)
from app.services.system.dept_service import dept_service

router = APIRouter()


@router.get("/list", summary="查看部门列表")
async def list_dept(
    query: DeptListQuery = Depends(),
    user: User = Depends(AuthControl.is_authed),
):
    """获取部门列表
    - 超级管理员：返回所有部门，或指定租户的部门
    - 普通用户：返回当前租户的部门
    """
    dept_tree = await dept_service.get_dept_tree(name=query.name)
    return Success(data=dept_tree)


@router.get("/get", summary="查看部门")
async def get_dept(
    query: DeptGetQuery = Depends(),
    user: User = Depends(AuthControl.is_authed),
):
    dept_data = await dept_service.get_by_id(query.id)
    return Success(data=dept_data)


@router.post("/create", summary="创建部门")
async def create_dept(
    dept_in: DeptCreate,
    user: User = Depends(AuthControl.is_authed),
):
    await dept_service.create(dept_in.model_dump())
    return Success(msg="Created Successfully")


@router.post("/update", summary="更新部门")
async def update_dept(
    dept_in: DeptUpdate,
    user: User = Depends(AuthControl.is_authed),
):
    await dept_service.update(dept_in.id, dept_in.model_dump(exclude={"id"}))
    return Success(msg="Update Successfully")


@router.delete("/delete", summary="删除部门")
async def delete_dept(
    query: DeptDeleteQuery = Depends(),
    user: User = Depends(AuthControl.is_authed),
):
    await dept_service.delete(query.dept_id)
    return Success(msg="Deleted Success")
