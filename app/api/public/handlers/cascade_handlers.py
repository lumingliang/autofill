"""
级联下拉相关接口
"""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException

from app.core.autofill_auth import APIKeyAuth
from app.core.request_parser import parse_request_params
from app.schemas.base import Success
from app.services.autofill.field_cascade_service import field_cascade_service
from app.log import logger

router = APIRouter()


@router.post("/autofill/cascade/config/create", summary="创建级联配置")
async def create_cascade_config(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
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
    params = await parse_request_params(request)
    
    try:
        result = await field_cascade_service.create_cascade_config(
            tenant_id=auth_info["tenant_id"],
            app_name=auth_info["app_name"],
            parent_field_id=params.get("parent_field_id"),
            parent_field_group_id=params.get("parent_field_group_id"),
            field_name_suffix=params.get("field_name_suffix", "-子字段"),
            field_label_prefix=params.get("field_label_prefix", ""),
            api_curl=params.get("api_curl", ""),
            api_params_mapping=params.get("api_params_mapping"),
            field_mapping=params.get("field_mapping"),
            enable_flatten=params.get("enable_flatten", False),
            flatten_config=params.get("flatten_config")
        )
        return Success(data=result)
    except Exception as e:
        logger.error(f"创建级联配置失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/autofill/cascade/config/update", summary="更新级联配置")
async def update_cascade_config(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
) -> Success:
    """更新级联配置"""
    params = await parse_request_params(request)
    
    try:
        result = await field_cascade_service.update_cascade_config(
            config_id=params.get("config_id"),
            tenant_id=auth_info["tenant_id"],
            **params
        )
        return Success(data=result)
    except Exception as e:
        logger.error(f"更新级联配置失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/autofill/cascade/config/list", summary="获取级联配置列表")
async def list_cascade_configs(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
) -> Success:
    """
    获取级联配置列表

    请求参数：
    {
        "parent_field_id": 1  // 可选，过滤指定父字段的配置
    }
    """
    params = await parse_request_params(request)
    
    try:
        configs = await field_cascade_service.get_cascade_configs(
            tenant_id=auth_info["tenant_id"],
            app_name=auth_info["app_name"],
            parent_field_id=params.get("parent_field_id")
        )
        return Success(data={"configs": configs})
    except Exception as e:
        logger.error(f"获取级联配置列表失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/autofill/cascade/config/delete", summary="删除级联配置")
async def delete_cascade_config(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
) -> Success:
    """删除级联配置"""
    params = await parse_request_params(request)
    
    try:
        result = await field_cascade_service.delete_cascade_config(
            config_id=params.get("config_id"),
            tenant_id=auth_info["tenant_id"]
        )
        return Success(data=result)
    except Exception as e:
        logger.error(f"删除级联配置失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/autofill/cascade/sync", summary="同步级联字段")
async def sync_cascade_fields(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
) -> Success:
    """
    同步级联字段

    请求参数：
    {
        "config_id": 1
    }
    """
    params = await parse_request_params(request)
    
    try:
        result = await field_cascade_service.sync_cascade_fields(
            config_id=params.get("config_id"),
            tenant_id=auth_info["tenant_id"]
        )
        return Success(data=result)
    except Exception as e:
        logger.error(f"同步级联字段失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/autofill/cascade/data/list", summary="获取级联数据")
async def list_cascade_data(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
) -> Success:
    """
    获取级联数据

    请求参数：
    {
        "config_id": 1
    }
    """
    params = await parse_request_params(request)
    
    try:
        data_list = await field_cascade_service.get_cascade_data(
            config_id=params.get("config_id"),
            tenant_id=auth_info["tenant_id"]
        )
        return Success(data={"cascade_data": data_list})
    except Exception as e:
        logger.error(f"获取级联数据失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/autofill/flatten/config/create", summary="创建字段展平配置")
async def create_flatten_config(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
) -> Success:
    """
    为单个字段创建展平配置

    请求参数：
    {
        "field_spec_id": 1,
        "label_path_level1": "$.data[*].label",
        "label_path_level2": "",
        "label_path_level3": "",
        "label_separator": "-",
        "value_path_level1": "$.data[*].value",
        "value_path_level2": "",
        "value_path_level3": "",
        "value_separator": "-"
    }
    """
    from app.models.autofill import FieldFlattenConfig
    from app.models.autofill import FieldSpec
    
    params = await parse_request_params(request)
    
    try:
        # 检查字段是否存在
        field = await FieldSpec.filter(
            id=params.get("field_spec_id"),
            tenant_id=auth_info["tenant_id"]
        ).first()
        
        if not field:
            raise ValueError("字段不存在")
        
        # 删除旧配置
        await FieldFlattenConfig.filter(
            field_spec_id=params.get("field_spec_id"),
            tenant_id=auth_info["tenant_id"]
        ).delete()
        
        # 创建新配置
        config = await FieldFlattenConfig.create(
            field_spec_id=params.get("field_spec_id"),
            tenant_id=auth_info["tenant_id"],
            app_name=auth_info["app_name"],
            label_path_level1=params.get("label_path_level1", ""),
            label_path_level2=params.get("label_path_level2", ""),
            label_path_level3=params.get("label_path_level3", ""),
            label_separator=params.get("label_separator", "-"),
            value_path_level1=params.get("value_path_level1", ""),
            value_path_level2=params.get("value_path_level2", ""),
            value_path_level3=params.get("value_path_level3", ""),
            value_separator=params.get("value_separator", "-"),
            is_active=True
        )
        
        return Success(data={
            "success": True,
            "config_id": config.id
        })
    except Exception as e:
        logger.error(f"创建展平配置失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/autofill/flatten/config/get", summary="获取字段展平配置")
async def get_flatten_config(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
) -> Success:
    """
    获取字段的展平配置

    请求参数：
    {
        "field_spec_id": 1
    }
    """
    from app.models.autofill import FieldFlattenConfig
    
    params = await parse_request_params(request)
    
    try:
        config = await FieldFlattenConfig.filter(
            field_spec_id=params.get("field_spec_id"),
            tenant_id=auth_info["tenant_id"],
            is_active=True
        ).first()
        
        if config:
            return Success(data={
                "config": {
                    "id": config.id,
                    "field_spec_id": config.field_spec_id,
                    "label_path_level1": config.label_path_level1,
                    "label_path_level2": config.label_path_level2,
                    "label_path_level3": config.label_path_level3,
                    "label_separator": config.label_separator,
                    "value_path_level1": config.value_path_level1,
                    "value_path_level2": config.value_path_level2,
                    "value_path_level3": config.value_path_level3,
                    "value_separator": config.value_separator
                }
            })
        else:
            return Success(data={"config": None})
    except Exception as e:
        logger.error(f"获取展平配置失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
