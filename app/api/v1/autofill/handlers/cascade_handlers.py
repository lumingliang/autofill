"""
级联下拉相关接口 (v1 版本，使用 Token 认证)
"""
from typing import Any, Dict, List
from fastapi import APIRouter, Query, Header
from fastapi.exceptions import HTTPException

from app.core.dependency import AuthControl, build_tenant_query
from app.schemas.base import Success
from app.services.autofill.field_cascade_service import field_cascade_service
from app.log import logger

router = APIRouter()


@router.post("/cascade/config/create", summary="创建级联配置")
async def create_cascade_config(
    data: Dict[str, Any],
    token: str = Header(..., description="token验证"),
) -> Success:
    """
    创建级联下拉配置

    请求参数：
    {
        "parent_field_id": 1,
        "parent_field_group_id": 1,
        "field_name_suffix": "-子字段",
        "field_label_prefix": "",
        "api_curl": "curl ...",
        "api_params_mapping": {
            "parentEventId": "{parent_value}"
        },
        "field_mapping": {
            "label_path": "$.data[*].label",
            "value_path": "$.data[*].value"
        },
        "enable_flatten": false,
        "flatten_config": {
            "label_path_level1": "",
            "label_path_level2": "",
            "label_path_level3": "",
            "label_separator": "-",
            "value_path_level1": "",
            "value_path_level2": "",
            "value_path_level3": "",
            "value_separator": "-"
        }
    }
    """
    auth_info = await AuthControl.is_authed(token)

    try:
        result = await field_cascade_service.create_cascade_config(
            tenant_id=auth_info["current_tenant_id"],
            app_name=data.get("app_name", "autofill"),
            parent_field_id=data.get("parent_field_id"),
            parent_field_group_id=data.get("parent_field_group_id"),
            field_name_suffix=data.get("field_name_suffix", "-子字段"),
            field_label_prefix=data.get("field_label_prefix", ""),
            api_curl=data.get("api_curl", ""),
            api_params_mapping=data.get("api_params_mapping"),
            field_mapping=data.get("field_mapping"),
            enable_flatten=data.get("enable_flatten", False),
            flatten_config=data.get("flatten_config")
        )
        return Success(data=result)
    except Exception as e:
        logger.error(f"创建级联配置失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cascade/config/update", summary="更新级联配置")
async def update_cascade_config(
    data: Dict[str, Any],
    token: str = Header(..., description="token验证"),
) -> Success:
    """更新级联配置"""
    auth_info = await AuthControl.is_authed(token)

    try:
        result = await field_cascade_service.update_cascade_config(
            config_id=data.get("config_id"),
            tenant_id=auth_info["current_tenant_id"],
            **data
        )
        return Success(data=result)
    except Exception as e:
        logger.error(f"更新级联配置失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cascade/config/list", summary="获取级联配置列表")
async def list_cascade_configs(
    parent_field_id: int = Query(0, description="父字段ID（可选）"),
    token: str = Header(..., description="token验证"),
) -> Success:
    """
    获取级联配置列表
    """
    auth_info = await AuthControl.is_authed(token)

    try:
        configs = await field_cascade_service.get_cascade_configs(
            tenant_id=auth_info["current_tenant_id"],
            app_name="autofill",
            parent_field_id=parent_field_id if parent_field_id > 0 else None
        )
        return Success(data={"configs": configs})
    except Exception as e:
        logger.error(f"获取级联配置列表失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/cascade/config/delete", summary="删除级联配置")
async def delete_cascade_config(
    config_id: int = Query(..., description="配置ID"),
    token: str = Header(..., description="token验证"),
) -> Success:
    """删除级联配置"""
    auth_info = await AuthControl.is_authed(token)

    try:
        result = await field_cascade_service.delete_cascade_config(
            config_id=config_id,
            tenant_id=auth_info["current_tenant_id"]
        )
        return Success(data=result)
    except Exception as e:
        logger.error(f"删除级联配置失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cascade/sync", summary="同步级联字段")
async def sync_cascade_fields(
    data: Dict[str, Any],
    token: str = Header(..., description="token验证"),
) -> Success:
    """
    同步级联字段

    请求参数：
    {
        "config_id": 1
    }
    """
    auth_info = await AuthControl.is_authed(token)

    try:
        result = await field_cascade_service.sync_cascade_fields(
            config_id=data.get("config_id"),
            tenant_id=auth_info["current_tenant_id"]
        )
        return Success(data=result)
    except Exception as e:
        logger.error(f"同步级联字段失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cascade/data/list", summary="获取级联数据")
async def list_cascade_data(
    config_id: int = Query(..., description="配置ID"),
    token: str = Header(..., description="token验证"),
) -> Success:
    """
    获取级联数据
    """
    auth_info = await AuthControl.is_authed(token)

    try:
        data_list = await field_cascade_service.get_cascade_data(
            config_id=config_id,
            tenant_id=auth_info["current_tenant_id"]
        )
        return Success(data={"cascade_data": data_list})
    except Exception as e:
        logger.error(f"获取级联数据失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
