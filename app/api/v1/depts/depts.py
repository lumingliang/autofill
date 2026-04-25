from fastapi import APIRouter, Header, Query
from tortoise.expressions import Q

from app.controllers.dept import dept_controller
from app.core.dependency import AuthControl
from app.models.admin import Dept, User
from app.schemas import Success
from app.schemas.depts import *

router = APIRouter()


def is_superuser(user: User) -> bool:
    """检查是否为超级管理员"""
    return user.is_superuser


@router.get("/list", summary="查看部门列表")
async def list_dept(
    name: str = Query(None, description="部门名称"),
    tenant_id: int = Query(None, description="租户ID（仅超级管理员可用）"),
    token: str = Header(..., description="token验证"),
):
    """获取部门列表
    - 超级管理员：返回所有部门，或指定租户的部门
    - 普通用户：返回当前租户的部门
    """
    current_user: User = await AuthControl.is_authed(token)

    # 构建查询条件
    q = Q(is_deleted=False)
    if name:
        q &= Q(name__contains=name)

    # 数据隔离：非超级管理员只能看到当前租户的部门
    if not is_superuser(current_user):
        if current_user.current_tenant_id:
            q &= Q(tenant_id=current_user.current_tenant_id)
        else:
            # 如果没有选择租户，返回空列表
            return Success(data=[])
        # 普通用户不显示租户名称
        dept_tree = await dept_controller.get_dept_tree_with_query(q, include_tenant=False)
    else:
        # 超级管理员可以通过 tenant_id 参数筛选特定租户的部门
        if tenant_id is not None:
            q &= Q(tenant_id=tenant_id)
        # 超级管理员显示租户名称
        dept_tree = await dept_controller.get_dept_tree_with_query(q, include_tenant=True)

    return Success(data=dept_tree)


@router.get("/get", summary="查看部门")
async def get_dept(
    id: int = Query(..., description="部门ID"),
    token: str = Header(..., description="token验证"),
):
    current_user: User = await AuthControl.is_authed(token)
    dept_obj = await dept_controller.get(id=id)

    # 数据隔离：非超级管理员只能查看自己租户的部门
    if not is_superuser(current_user):
        if dept_obj.tenant_id != current_user.current_tenant_id:
            return Success(code=403, msg="您没有权限查看该部门")

    data = await dept_obj.to_dict()
    return Success(data=data)


@router.post("/create", summary="创建部门")
async def create_dept(
    dept_in: DeptCreate,
    token: str = Header(..., description="token验证"),
):
    current_user: User = await AuthControl.is_authed(token)

    # 数据隔离：非超级管理员创建的部门自动归属当前租户
    if not is_superuser(current_user):
        dept_in.tenant_id = current_user.current_tenant_id

    await dept_controller.create_dept(obj_in=dept_in)
    return Success(msg="Created Successfully")


@router.post("/update", summary="更新部门")
async def update_dept(
    dept_in: DeptUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user: User = await AuthControl.is_authed(token)
    dept_obj = await dept_controller.get(id=dept_in.id)

    # 数据隔离：非超级管理员只能更新自己租户的部门
    if not is_superuser(current_user):
        if dept_obj.tenant_id != current_user.current_tenant_id:
            return Success(code=403, msg="您没有权限更新该部门")
        # 非超级管理员不能修改租户ID
        dept_in.tenant_id = current_user.current_tenant_id

    await dept_controller.update_dept(obj_in=dept_in)
    return Success(msg="Update Successfully")


@router.delete("/delete", summary="删除部门")
async def delete_dept(
    dept_id: int = Query(..., description="部门ID"),
    token: str = Header(..., description="token验证"),
):
    current_user: User = await AuthControl.is_authed(token)
    dept_obj = await dept_controller.get(id=dept_id)

    # 数据隔离：非超级管理员只能删除自己租户的部门
    if not is_superuser(current_user):
        if dept_obj.tenant_id != current_user.current_tenant_id:
            return Success(code=403, msg="您没有权限删除该部门")

    await dept_controller.delete_dept(dept_id=dept_id)
    return Success(msg="Deleted Success")
