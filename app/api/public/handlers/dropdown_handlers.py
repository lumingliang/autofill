"""
下拉选项相关接口
全部采用POST路由，请求参数使用schema定义
"""
from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException
from tortoise.expressions import Q

from app.controllers.autofill import dropdown_option_controller
from app.core.autofill_auth import APIKeyAuth
from app.core.request_parser import parse_request_params
from app.schemas.base import Success
from app.schemas.public import (
    DropdownOptionListRequest,
    DropdownOptionDetailRequest,
    FirstLevelMenusRequest,
    SubmenusTreeRequest,
)

router = APIRouter()


async def build_dropdown_tree(tenant_id: int, app_name: str, parent_id: int) -> list:
    """递归构建下拉选项树形结构"""
    children = await dropdown_option_controller.model.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        parent_id=parent_id
    ).all()

    result = []
    for child in children:
        child_dict = {
            "id": child.id,
            "option_value": child.option_value,
            "summary": child.summary,
        }
        sub_children = await build_dropdown_tree(tenant_id, app_name, child.id)
        if sub_children:
            child_dict["children"] = sub_children
        result.append(child_dict)
    return result


async def list_dropdown_options_handler(request: Request, auth_info: dict):
    """
    查询下拉选项列表处理逻辑
    支持扁平列表和树形结构两种返回格式
    """
    params = await parse_request_params(request, DropdownOptionListRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    q = Q(tenant_id=tenant_id, app_name=app_name)
    if params.get("class_name"):
        q &= Q(class_name=params["class_name"])

    parent_id = params.get("parent_id", 0)
    q &= Q(parent_id=parent_id)

    is_tree = params.get("tree", False)

    if is_tree:
        tree_data = await build_dropdown_tree(tenant_id, app_name, parent_id)
        return Success(data=tree_data)
    else:
        options = await dropdown_option_controller.model.filter(q).all()
        return Success(data=[
            {
                "id": o.id,
                "option_value": o.option_value,
                "summary": o.summary,
                "has_children": await dropdown_option_controller.model.filter(parent_id=o.id).exists()
            }
            for o in options
        ])


@router.post("/autofill/dropdown_options/list", summary="查询下拉选项列表")
async def list_dropdown_options(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    Dify调用: 根据 app_name + class_name + parent_id 查询下拉选项列表
    只支持 POST 方法
    支持参数传递方式: JSON Body
    """
    return await list_dropdown_options_handler(request, auth_info)


async def get_dropdown_option_handler(request: Request, auth_info: dict):
    """查询下拉选项详情处理逻辑"""
    params = await parse_request_params(request, DropdownOptionDetailRequest)

    option = await dropdown_option_controller.model.filter(
        id=params["id"],
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"]
    ).first()

    if not option:
        raise HTTPException(status_code=404, detail="Option not found")

    children = await dropdown_option_controller.model.filter(
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"],
        parent_id=option.id
    ).all()

    return Success(data={
        "id": option.id,
        "option_value": option.option_value,
        "summary": option.summary,
        "description": option.description,
        "class_name": option.class_name,
        "children": [
            {"id": c.id, "option_value": c.option_value, "summary": c.summary}
            for c in children
        ]
    })


@router.post("/autofill/dropdown_options", summary="查询下拉选项详情")
async def get_dropdown_option(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    Dify调用: 根据ID查询选项详情及其子选项
    只支持 POST 方法
    支持参数传递方式: JSON Body
    """
    return await get_dropdown_option_handler(request, auth_info)


# ==================== 下拉选项层级接口 ====================

async def list_first_level_menus_handler(request: Request, auth_info: dict):
    """A1. 获取所有一级菜单"""
    params = await parse_request_params(request, FirstLevelMenusRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    q = Q(tenant_id=tenant_id, app_name=app_name, parent_id=0)
    if params.get("class_name"):
        q &= Q(class_name=params["class_name"])

    options = await dropdown_option_controller.model.filter(q).all()

    return Success(data=[
        {
            "id": o.id,
            "option_value": o.option_value,
            "summary": o.summary,
            "class_name": o.class_name,
        }
        for o in options
    ])


@router.post("/autofill/dropdown/first_level", summary="A1. 获取所有一级菜单")
async def list_first_level_menus(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    获取所有一级菜单（parent_id=0 的选项）
    只支持 POST 方法
    支持参数传递方式: JSON Body
    """
    return await list_first_level_menus_handler(request, auth_info)


async def get_submenus_tree_handler(request: Request, auth_info: dict):
    """A2. 根据一级菜单名称+应用名称+分类获取二三级菜单（树形结构）"""
    params = await parse_request_params(request, SubmenusTreeRequest)

    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]
    first_level_value = params.get("first_level_value")
    class_name = params.get("class_name", "")

    if not first_level_value:
        raise HTTPException(status_code=400, detail="first_level_value is required")

    q = Q(
        tenant_id=tenant_id,
        app_name=app_name,
        parent_id=0,
        option_value=first_level_value
    )
    if class_name:
        q &= Q(class_name=class_name)

    first_level = await dropdown_option_controller.model.filter(q).first()

    if not first_level:
        raise HTTPException(status_code=404, detail="First level menu not found")

    tree_data = await build_dropdown_tree(tenant_id, app_name, first_level.id)

    return Success(data={
        "first_level": {
            "id": first_level.id,
            "option_value": first_level.option_value,
            "summary": first_level.summary,
            "class_name": first_level.class_name,
        },
        "children": tree_data
    })


@router.post("/autofill/dropdown/submenus_tree", summary="A2. 获取二三级菜单树形结构")
async def get_submenus_tree(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    根据一级菜单名称+应用名称+分类获取二三级菜单（树形结构）
    只支持 POST 方法
    支持参数传递方式: JSON Body
    """
    return await get_submenus_tree_handler(request, auth_info)


# ==================== 标准下拉列表接口（用于OpenAPI同步）====================

@router.get("/common/dict/event-type", summary="获取事件类型下拉列表")
async def get_event_type_list(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    返回用于前端下拉选择框的事件类型枚举列表
    标准格式: { "code": 200, "message": "操作成功", "data": [{"label": "", "value": ""}] }
    必须携带固定鉴权Header
    支持查询参数: app_name, class_name, parent_id
    """
    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 获取查询参数（静态参数）
    params = dict(request.query_params)
    query_app_name = params.get("app_name", app_name)
    query_class_name = params.get("class_name", "event_type")
    parent_id = int(params.get("parent_id", 0))

    # 查询下拉选项列表（支持通过参数指定分类）
    options = await dropdown_option_controller.model.filter(
        tenant_id=tenant_id,
        app_name=query_app_name,
        class_name=query_class_name,
        parent_id=parent_id
    ).all()

    # 转换为标准下拉格式
    data = [
        {
            "label": option.summary or option.option_value,
            "value": option.option_value
        }
        for option in options
    ]

    # 如果没有数据，返回示例数据
    if not data:
        data = [
            {"label": "会议事件", "value": "MEETING"},
            {"label": "培训事件", "value": "TRAINING"},
            {"label": "团建事件", "value": "TEAM_BUILDING"},
            {"label": "其他事件", "value": "OTHER"}
        ]

    return {
        "code": 200,
        "message": "操作成功",
        "data": data
    }
