"""
级联下拉相关接口 (v1 版本)
"""
from fastapi import APIRouter, Query, Header
from fastapi.exceptions import HTTPException

from app.core.dependency import AuthControl
from app.core.tenant import TenantContext
from app.schemas.base import Success
from app.services.autofill.field_cascade_service import field_cascade_service
from app.log import logger

router = APIRouter()


@router.post("/cascade/config/create", summary="创建级联配置")
async def create_cascade_config(data: dict, token: str = Header(...)) -> Success:
    user = await AuthControl.is_authed(token)

    try:
        result = await field_cascade_service.create_cascade_config(
            parent_field_id=data.get("parent_field_id"),
            parent_field_group_id=data.get("parent_field_group_id"),
            field_name_pattern=data.get("field_name_pattern", "parent.$.data[*].label + -的二三级"),
            field_label_pattern=data.get("field_label_pattern", "parent.$.data[*].value + -的二三级"),
            api_headers=data.get("api_headers"),
            api_schema=data.get("api_schema", ""),
            enable_flatten=data.get("enable_flatten", False),
            flatten_config=data.get("flatten_config")
        )
        return Success(data=result)
    except Exception as e:
        logger.error(f"创建级联配置失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cascade/config/update", summary="更新级联配置")
async def update_cascade_config(data: dict, token: str = Header(...)) -> Success:
    user = await AuthControl.is_authed(token)

    try:
        result = await field_cascade_service.update_cascade_config(
            config_id=data.pop("id", None),
            **data
        )
        return Success(data=result)
    except Exception as e:
        logger.error(f"更新级联配置失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cascade/config/list", summary="获取级联配置列表")
async def list_cascade_configs(
    parent_field_id: int = Query(..., description="父字段ID"),
    token: str = Header(...)
) -> Success:
    user = await AuthControl.is_authed(token)

    try:
        configs = await field_cascade_service.get_cascade_configs(
            parent_field_id=parent_field_id
        )
        return Success(data={"configs": configs})
    except Exception as e:
        logger.error(f"获取级联配置列表失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/cascade/config/delete", summary="删除级联配置")
async def delete_cascade_config(
    config_id: int = Query(..., description="级联配置ID"),
    token: str = Header(...)
) -> Success:
    user = await AuthControl.is_authed(token)

    try:
        result = await field_cascade_service.delete_cascade_config(
            config_id=config_id
        )
        return Success(data=result)
    except Exception as e:
        logger.error(f"删除级联配置失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cascade/sync", summary="同步级联字段")
async def sync_cascade_fields(data: dict, token: str = Header(...)) -> Success:
    user = await AuthControl.is_authed(token)

    try:
        result = await field_cascade_service.sync_cascade_fields(
            config_id=data.get("config_id")
        )
        return Success(data=result)
    except Exception as e:
        logger.error(f"同步级联字段失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cascade/data/list", summary="获取级联数据")
async def list_cascade_data(
    config_id: int = Query(..., description="级联配置ID"),
    token: str = Header(...)
) -> Success:
    user = await AuthControl.is_authed(token)

    try:
        data_list = await field_cascade_service.get_cascade_data(
            config_id=config_id
        )
        return Success(data={"cascade_data": data_list})
    except Exception as e:
        logger.error(f"获取级联数据失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
