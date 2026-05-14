"""
级联下拉相关接口
"""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException

from app.core.autofill_auth import APIKeyAuth
from app.core.request_parser import parse_request_params
from app.schemas.base import Success, Fail
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


@router.post("/autofill/cascade/parse_curl", summary="解析 curl 命令生成 OpenAPI Schema")
async def parse_curl_for_cascade(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
) -> Success:
    """
    解析 curl 命令，执行请求，并生成 OpenAPI Schema (YAML格式)

    请求参数：
    {
        "curl_command": "curl -X GET http://api.example.com/data ...",
        "label_path": "$.data[*].label",
        "value_path": "$.data[*].value",
        "enable_flatten": false,
        "flatten_config": {
            "label_path_level1": "$.data[*].label",
            "label_path_level2": "$.data[*].children[*].label",
            "label_path_level3": "",
            "label_separator": "-",
            "value_path_level1": "$.data[*].value",
            "value_path_level2": "$.data[*].children[*].value",
            "value_path_level3": "",
            "value_separator": "-"
        }
    }

    返回：
    {
        "openapi_schema": "openapi: 3.0.0...",
        "response_preview": {...},
        "message": "解析成功"
    }
    """
    import httpx
    import yaml
    from app.utils.curl_parser import parse_curl_command, generate_openapi_schema_from_curl

    params = await parse_request_params(request)
    curl_command = params.get("curl_command", "")

    if not curl_command or not curl_command.strip():
        return Fail(code=400, msg="curl 命令不能为空")

    try:
        # 1. 解析 curl 命令
        parsed = parse_curl_command(curl_command)

        # 2. 执行 HTTP 请求
        async with httpx.AsyncClient(timeout=30.0) as client:
            method = parsed['method'].lower()
            url = parsed['url']
            headers = parsed['headers']
            body = parsed['body']

            if method == 'get':
                response = await client.get(url, headers=headers)
            elif method == 'post':
                if body and isinstance(body, dict):
                    response = await client.post(url, headers=headers, json=body)
                else:
                    response = await client.post(url, headers=headers)
            elif method == 'put':
                if body and isinstance(body, dict):
                    response = await client.put(url, headers=headers, json=body)
                else:
                    response = await client.put(url, headers=headers)
            elif method == 'patch':
                if body and isinstance(body, dict):
                    response = await client.patch(url, headers=headers, json=body)
                else:
                    response = await client.patch(url, headers=headers)
            elif method == 'delete':
                response = await client.delete(url, headers=headers)
            else:
                return Fail(code=400, msg=f"不支持的 HTTP 方法: {method}")

            response.raise_for_status()
            response_data = response.json()

        # 3. 构建展平配置
        flatten_config = None
        enable_flatten = params.get("enable_flatten", False)
        if enable_flatten:
            flatten_config = params.get("flatten_config", {})

        # 4. 生成 OpenAPI Schema
        openapi_dict = generate_openapi_schema_from_curl(
            curl_command,
            response_data,
            label_path=params.get("label_path", "$.data[*].label"),
            value_path=params.get("value_path", "$.data[*].value"),
            enable_flatten=enable_flatten,
            flatten_config=flatten_config
        )

        # 5. 转换为 YAML 格式
        openapi_yaml = yaml.dump(openapi_dict, allow_unicode=True, sort_keys=False)

        return Success(data={
            "openapi_schema": openapi_yaml,
            "response_preview": response_data,
            "message": "curl 解析成功，已生成 OpenAPI Schema"
        })

    except ValueError as e:
        return Fail(code=400, msg=f"curl 命令解析错误: {str(e)}")
    except httpx.HTTPError as e:
        return Fail(code=400, msg=f"执行 curl 请求失败: {str(e)}")
    except Exception as e:
        logger.error(f"解析 curl 失败: {e}")
        return Fail(code=500, msg=f"解析失败: {str(e)}")


@router.post("/autofill/cascade/sync_from_schema", summary="根据 OpenAPI Schema 同步级联选项")
async def sync_cascade_from_schema(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
) -> Success:
    """
    根据 OpenAPI Schema 配置从 API 同步级联下拉选项

    请求参数：
    {
        "config_id": 1,  // 级联配置ID
        "openapi_schema": "openapi: 3.0.0...",  // OpenAPI Schema (YAML格式)
        "api_headers": [{"key": "Authorization", "value": "Bearer xxx"}],  // 可选，额外请求头
        "label_path": "$.data[*].label",  // 标签路径
        "value_path": "$.data[*].value",  // 值路径
        "enable_flatten": false,  // 是否启用展平
        "flatten_config": {  // 展平配置
            "label_path_level1": "$.data[*].label",
            "label_path_level2": "$.data[*].children[*].label",
            "label_separator": "-",
            "value_path_level1": "$.data[*].value",
            "value_path_level2": "$.data[*].children[*].value",
            "value_separator": "-"
        }
    }

    返回：
    {
        "success": true,
        "synced_count": 5,
        "total_count": 5,
        "results": [...]
    }
    """
    import tempfile
    import os
    import httpx
    import yaml
    import prance
    from jsonpath_ng import parse as jsonpath_parse
    from app.services.autofill.field_flatten_service import FieldFlattener

    params = await parse_request_params(request)
    config_id = params.get("config_id")
    openapi_schema = params.get("openapi_schema", "")

    if not config_id:
        return Fail(code=400, msg="config_id 不能为空")

    if not openapi_schema:
        return Fail(code=400, msg="openapi_schema 不能为空")

    try:
        # 1. 解析 OpenAPI Schema
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(openapi_schema)
            temp_path = f.name

        try:
            parser = prance.ResolvingParser(temp_path, backend='openapi-spec-validator')
            spec = parser.specification
        finally:
            os.unlink(temp_path)

        # 2. 获取端点配置
        servers = spec.get('servers', [])
        base_url = servers[0].get('url', '') if servers else ''

        paths = spec.get('paths', {})
        if not paths:
            return Fail(code=400, msg="Schema中未找到paths配置")

        path, methods = next(iter(paths.items()))
        method = 'get' if 'get' in methods else 'post'
        operation = methods.get(method, {})

        full_url = f"{base_url.rstrip('/')}{path}"

        # 3. 从 x-api-params 获取固定参数和 headers
        x_api_params = operation.get('x-api-params', {})
        headers = x_api_params.get('headers', {}).copy()

        # 合并额外传入的 headers
        for h in (params.get("api_headers") or []):
            if h.get("key") and h.get("value"):
                headers[h["key"]] = h["value"]

        # 4. 获取字段映射配置
        x_mapping = operation.get('x-field-mapping', {})
        label_path = x_mapping.get('label_path', params.get("label_path", "$.data[*].label"))
        value_path = x_mapping.get('value_path', params.get("value_path", "$.data[*].value"))
        enable_flatten = x_mapping.get('enable_flatten', params.get("enable_flatten", False))
        flatten_config = x_mapping.get('flatten_config', params.get("flatten_config"))

        # 5. 更新级联配置的 Schema 和字段映射
        await field_cascade_service.update_cascade_config(
            config_id=config_id,
            tenant_id=auth_info["tenant_id"],
            api_schema=openapi_schema,
            field_mapping={
                "label_path": label_path,
                "value_path": value_path
            },
            enable_flatten=enable_flatten,
            flatten_config=flatten_config
        )

        # 6. 执行同步
        result = await field_cascade_service.sync_cascade_fields(
            config_id=config_id,
            tenant_id=auth_info["tenant_id"]
        )

        return Success(data=result)

    except ValueError as e:
        return Fail(code=400, msg=f"Schema解析错误: {str(e)}")
    except yaml.YAMLError as e:
        return Fail(code=400, msg=f"Schema YAML格式错误: {str(e)}")
    except Exception as e:
        logger.error(f"同步级联选项失败: {e}")
        return Fail(code=500, msg=f"同步失败: {str(e)}")


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
