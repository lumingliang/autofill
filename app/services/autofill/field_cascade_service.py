"""
级联下拉服务 - 处理多级级联下拉的同步和管理
"""
import os
import re
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional
from jsonpath_ng import parse as jsonpath_parse

import httpx
import prance

from tortoise.expressions import Q

from app.core.tenant import TenantContext
from app.log import logger
from app.models.autofill import (
    FieldCascadeConfig, FieldCascadeData,
    FieldSpec, FieldGroupConfig
)
from app.services.autofill.field_flatten_service import FieldFlattener
from app.services.autofill.field_spec_service import upsert_field_spec


class FieldCascadeService:
    """级联下拉服务类"""

    def __init__(self):
        self.flattener = FieldFlattener()

    async def create_cascade_config(
        self,
        tenant_id: int,
        app_name: str,
        parent_field_id: int,
        parent_field_group_id: int,
        field_name_pattern: str = "parent.$.data[*].label + -的二三级",
        field_label_pattern: str = "parent.$.data[*].value + -的二三级",
        api_headers: Optional[List[Dict[str, str]]] = None,
        api_schema: str = "",
        enable_flatten: bool = False,
        flatten_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        parent_field = await FieldSpec.filter(id=parent_field_id).first()
        parent_group = await FieldGroupConfig.filter(id=parent_field_group_id).first()

        if not parent_field:
            raise ValueError("父字段不存在")
        if not parent_group:
            raise ValueError("父字段组不存在")

        api_method = "GET"
        api_url = ""

        if api_schema:
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write(api_schema)
                    temp_path = f.name

                try:
                    parser = prance.ResolvingParser(temp_path, backend='openapi-spec-validator')
                    spec = parser.specification

                    servers = spec.get('servers', [])
                    base_url = servers[0].get('url', '') if servers else ''

                    paths = spec.get('paths', {})
                    if paths:
                        path, methods = next(iter(paths.items()))
                        method = 'get' if 'get' in methods else 'post'

                        api_url = f"{base_url.rstrip('/')}{path}"
                        api_method = method.upper()
                finally:
                    os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"解析 api_schema 失败: {e}")

        config = await FieldCascadeConfig.create(
            tenant_id=tenant_id,
            app_name=app_name,
            parent_field_id=parent_field_id,
            parent_field_name=parent_field.field_name,
            parent_field_group_id=parent_field_group_id,
            field_name_pattern=field_name_pattern,
            field_label_pattern=field_label_pattern,
            api_headers=api_headers or [],
            api_schema=api_schema,
            api_method=api_method,
            api_url=api_url,
            enable_flatten=enable_flatten,
            flatten_config=flatten_config or {},
            is_active=True
        )

        logger.info(f"[FieldCascadeService] 创建级联配置成功: config_id={config.id}")

        return {
            "success": True,
            "cascade_config_id": config.id,
            "parent_field_name": parent_field.field_name
        }

    async def get_cascade_configs(
        self,
        tenant_id: int,
        app_name: str,
        parent_field_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        query = Q(tenant_id=tenant_id, app_name=app_name, is_active=True)

        if parent_field_id:
            query &= Q(parent_field_id=parent_field_id)

        configs = await FieldCascadeConfig.filter(query).all()

        return [
            {
                "id": config.id,
                "parent_field_id": config.parent_field_id,
                "parent_field_name": config.parent_field_name,
                "parent_field_group_id": config.parent_field_group_id,
                "field_name_pattern": config.field_name_pattern,
                "field_label_pattern": config.field_label_pattern,
                "api_url": config.api_url,
                "api_headers": config.api_headers,
                "api_schema": config.api_schema,
                "enable_flatten": config.enable_flatten,
                "flatten_config": config.flatten_config,
                "last_sync_at": config.last_sync_at.isoformat() if config.last_sync_at else None,
                "is_active": config.is_active
            }
            for config in configs
        ]

    async def update_cascade_config(
        self,
        config_id: int,
        tenant_id: int,
        **kwargs
    ) -> Dict[str, Any]:
        config = await FieldCascadeConfig.filter(id=config_id, tenant_id=tenant_id).first()
        if not config:
            raise ValueError("级联配置不存在")

        if "api_schema" in kwargs and kwargs["api_schema"]:
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write(kwargs["api_schema"])
                    temp_path = f.name

                try:
                    parser = prance.ResolvingParser(temp_path, backend='openapi-spec-validator')
                    spec = parser.specification

                    servers = spec.get('servers', [])
                    base_url = servers[0].get('url', '') if servers else ''

                    paths = spec.get('paths', {})
                    if paths:
                        path, methods = next(iter(paths.items()))
                        method = 'get' if 'get' in methods else 'post'

                        kwargs["api_url"] = f"{base_url.rstrip('/')}{path}"
                        kwargs["api_method"] = method.upper()
                finally:
                    os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"解析 api_schema 失败: {e}")

        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        await config.save()

        logger.info(f"[FieldCascadeService] 更新级联配置成功: config_id={config_id}")

        return {
            "success": True,
            "cascade_config_id": config_id
        }

    async def delete_cascade_config(
        self,
        config_id: int,
        tenant_id: int
    ) -> Dict[str, Any]:
        config = await FieldCascadeConfig.filter(id=config_id, tenant_id=tenant_id).first()
        if not config:
            raise ValueError("级联配置不存在")

        config.is_active = False
        await config.save()

        logger.info(f"[FieldCascadeService] 删除级联配置成功: config_id={config_id}")

        return {
            "success": True,
            "cascade_config_id": config_id
        }

    async def sync_cascade_fields(
        self,
        config_id: int,
        tenant_id: int
    ) -> Dict[str, Any]:
        config = await FieldCascadeConfig.filter(id=config_id, tenant_id=tenant_id).first()

        if not config:
            raise ValueError("级联配置不存在")

        logger.info(f"[FieldCascadeService] 开始同步级联字段: config_id={config_id}")

        parent_field = await FieldSpec.filter(id=config.parent_field_id).first()
        if not parent_field:
            raise ValueError("父字段不存在")

        parent_options = (parent_field.options or {}).get("items", []) if isinstance(parent_field.options, dict) else []
        if not parent_options:
            logger.warning("父字段没有选项")
            return {
                "success": True,
                "message": "父字段没有选项",
                "synced_count": 0
            }

        results = []
        success_count = 0

        for option in parent_options:
            if option.get("is_deleted", False):
                continue

            parent_label = option.get("label", "")
            parent_value = option.get("value", "")

            if not parent_value:
                continue

            try:
                sync_result = await self._sync_single_cascade_field(
                    config=config,
                    parent_field=parent_field,
                    parent_label=parent_label,
                    parent_value=parent_value,
                    parent_option=option
                )
                results.append(sync_result)

                if sync_result.get("success"):
                    success_count += 1

            except Exception as e:
                logger.error(f"同步选项 {parent_label} 失败: {e}")
                results.append({
                    "parent_label": parent_label,
                    "parent_value": parent_value,
                    "success": False,
                    "error": str(e)
                })

        config.last_sync_at = datetime.now()
        await config.save()

        logger.info(f"[FieldCascadeService] 级联同步完成: 成功 {success_count}/{len(results)}")

        return {
            "success": True,
            "synced_count": success_count,
            "total_count": len(results),
            "results": results
        }

    async def _sync_single_cascade_field(
        self,
        config: FieldCascadeConfig,
        parent_field: FieldSpec,
        parent_label: str,
        parent_value: str,
        parent_option: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        logger.info(f"[FieldCascadeService] 同步单个级联字段: parent_label={parent_label}")

        api_data = await self._call_cascade_api(
            config=config,
            parent_value=parent_value,
            parent_option=parent_option
        )

        if not api_data:
            raise ValueError("API返回数据为空")

        options = self._extract_options(
            api_data=api_data,
            config=config,
            enable_flatten=config.enable_flatten,
            flatten_config=config.flatten_config
        )

        if not options:
            logger.warning("未提取到选项")

        field_name_pattern = config.field_name_pattern or "parent.$.data[*].label + -的二三级"
        child_field_name = self._generate_field_name(field_name_pattern, parent_label, parent_value)

        # 使用字段标签规则生成标签，逻辑同字段名规则
        field_label_pattern = config.field_label_pattern or "parent.$.data[*].value + -的二三级"
        child_field_label = self._generate_field_label(field_label_pattern, parent_label, parent_value)

        # 使用父字段的字段类型，保持级联子字段与父字段类型一致
        parent_field_type = parent_field.field_type if parent_field else "select_single"

        upsert_result = await upsert_field_spec(
            tenant_id=config.tenant_id,
            app_name=config.app_name,
            field_name=child_field_name,
            field_label=child_field_label,
            field_type=parent_field_type,
            field_group_ids=[config.parent_field_group_id],
            fill_instruction=f"根据'{parent_label}'选择的子项",
            options={"items": options},
            sync_mode='replace'  # 级联字段同步使用 replace 模式，完全替换选项
        )

        logger.info(f"[FieldCascadeService] 同步单个级联字段成功: child_field={child_field_name}")

        return {
            "success": True,
            "parent_label": parent_label,
            "parent_value": parent_value,
            "child_field_id": upsert_result["field_spec"].id,
            "child_field_name": child_field_name,
            "options_count": len(options)
        }

    async def _call_cascade_api(
        self,
        config: FieldCascadeConfig,
        parent_value: str,
        parent_option: Dict[str, Any] = None
    ) -> Any:
        if config.api_schema:
            return await self._call_cascade_api_from_schema(
                config=config,
                parent_value=parent_value,
                parent_option=parent_option
            )

        raise ValueError("API配置无效，缺少 api_schema 配置")

    async def _call_cascade_api_from_schema(
        self,
        config: FieldCascadeConfig,
        parent_value: str,
        parent_option: Dict[str, Any] = None
    ) -> Any:
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(config.api_schema)
                temp_path = f.name

            try:
                parser = prance.ResolvingParser(temp_path, backend='openapi-spec-validator')
                spec = parser.specification
            finally:
                os.unlink(temp_path)

            servers = spec.get('servers', [])
            base_url = servers[0].get('url', '') if servers else ''

            paths = spec.get('paths', {})
            if not paths:
                raise ValueError("Schema中未找到paths配置")

            path, methods = next(iter(paths.items()))
            method = 'get' if 'get' in methods else 'post'
            operation = methods.get(method, {})

            full_url = f"{base_url.rstrip('/')}{path}"

            x_api_params = operation.get('x-api-params', {})
            headers = x_api_params.get('headers', {}).copy()

            params = {}
            for param_key, param_value in x_api_params.items():
                if param_key == 'headers':
                    continue

                if isinstance(param_value, str) and param_value.startswith('parent.$'):
                    # 支持 parent.$.data[*].value 格式，从父选项中提取值
                    # 去掉 parent. 前缀，得到真正的 JSONPath
                    json_path = param_value[7:]  # 去掉 'parent.' 前缀
                    extracted_values = self._apply_jsonpath(parent_option, json_path)
                    if extracted_values:
                        params[param_key] = str(extracted_values[0])
                    else:
                        params[param_key] = parent_value
                elif isinstance(param_value, str) and param_value.startswith('$'):
                    extracted_values = self._apply_jsonpath(parent_option, param_value)
                    if extracted_values:
                        params[param_key] = str(extracted_values[0])
                    else:
                        params[param_key] = parent_value
                elif isinstance(param_value, str) and '{parent_value}' in param_value:
                    params[param_key] = param_value.replace('{parent_value}', parent_value)
                else:
                    params[param_key] = param_value

            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == 'get':
                    response = await client.get(full_url, headers=headers, params=params)
                else:
                    headers.setdefault('Content-Type', 'application/json')
                    response = await client.post(full_url, headers=headers, json=params)

                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"根据 Schema 调用级联API失败: {e}")
            raise ValueError(f"API调用失败: {str(e)}")

    def _extract_options(
        self,
        api_data: Any,
        config: FieldCascadeConfig,
        enable_flatten: bool = False,
        flatten_config: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        从API响应数据中提取选项

        支持两种模式：
        1. 展平模式：使用 flatten_config 中的 label_path_level1/2/3 等配置
        2. 普通模式：使用 label_path 和 value_path 提取
        """
        try:
            # 默认路径
            label_path = "$.data[*].label"
            value_path = "$.data[*].value"
            field_mapping_spec = {}

            # 从 api_schema 中解析 x-field-mapping
            if config.api_schema:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write(config.api_schema)
                    temp_path = f.name

                try:
                    parser = prance.ResolvingParser(temp_path, backend='openapi-spec-validator')
                    spec = parser.specification

                    paths = spec.get('paths', {})
                    if paths:
                        path, methods = next(iter(paths.items()))
                        method = 'get' if 'get' in methods else 'post'
                        operation = methods.get(method, {})

                        field_mapping_spec = operation.get('x-field-mapping', {})
                        label_path = field_mapping_spec.get("label_path", label_path)
                        value_path = field_mapping_spec.get("value_path", value_path)
                        # 从 x-field-mapping 中读取 enable_flatten 和 flatten_config
                        mapping_enable_flatten = field_mapping_spec.get("enable_flatten", False)
                        mapping_flatten_config = field_mapping_spec.get("flatten_config", {})

                        # 如果 x-field-mapping 中有展平配置，优先使用
                        if mapping_enable_flatten and mapping_flatten_config:
                            enable_flatten = True
                            flatten_config = mapping_flatten_config
                finally:
                    os.unlink(temp_path)

            # 展平模式：使用 flatten_config 中的配置
            if enable_flatten and flatten_config:
                # 构建完整的 flatten_config，使用 label_path/value_path 作为默认值
                complete_flatten_config = {
                    "label_path_level1": flatten_config.get("label_path_level1") or label_path,
                    "label_path_level2": flatten_config.get("label_path_level2", ""),
                    "label_path_level3": flatten_config.get("label_path_level3", ""),
                    "label_separator": flatten_config.get("label_separator", "-"),
                    "value_path_level1": flatten_config.get("value_path_level1") or value_path,
                    "value_path_level2": flatten_config.get("value_path_level2", ""),
                    "value_path_level3": flatten_config.get("value_path_level3", ""),
                    "value_separator": flatten_config.get("value_separator", "-"),
                }

                logger.info(f"[_extract_options] 使用展平模式，配置: {complete_flatten_config}")
                return self.flattener.flatten_field_options(
                    data=api_data,
                    flatten_config=complete_flatten_config
                )

            # 普通模式：直接使用 label_path 和 value_path
            labels = self._apply_jsonpath(api_data, label_path)
            values = self._apply_jsonpath(api_data, value_path)

            options = []
            min_len = min(len(labels), len(values))
            for i in range(min_len):
                options.append({
                    "label": str(labels[i]) if labels[i] is not None else "",
                    "value": str(values[i]) if values[i] is not None else "",
                    "is_deleted": False
                })

            return options

        except Exception as e:
            logger.error(f"提取选项失败: {e}")

        return []

    @staticmethod
    def _apply_jsonpath(data: Any, json_path: str) -> List[Any]:
        if not json_path or not data:
            return []

        try:
            jsonpath_expr = jsonpath_parse(json_path)
            results = [match.value for match in jsonpath_expr.find(data)]
            return results if results else []
        except Exception as e:
            logger.warning(f"JSONPath解析失败: {e}")
            return []

    @staticmethod
    def _generate_field_name(field_name_pattern: str, parent_label: str, parent_value: str) -> str:
        parts = field_name_pattern.split('+')
        result = ""

        for part in parts:
            part = part.strip()
            if part.startswith("parent.$"):
                result += parent_label
            elif part.startswith("{") and part.endswith("}"):
                placeholder = part[1:-1].strip()
                if placeholder == "parent_value":
                    result += parent_value
                elif placeholder == "parent_label":
                    result += parent_label
            else:
                result += part

        result = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5]', '_', result)
        return result

    @staticmethod
    def _generate_field_label(field_label_pattern: str, parent_label: str, parent_value: str) -> str:
        """
        生成字段标签，逻辑同字段名规则，但保留原始字符（不进行下划线替换）
        
        Args:
            field_label_pattern: 字段标签规则，如 "parent.$.data[*].value + -的二三级"
            parent_label: 父选项标签
            parent_value: 父选项值
            
        Returns:
            生成的字段标签
        """
        parts = field_label_pattern.split('+')
        result = ""

        for part in parts:
            part = part.strip()
            if part.startswith("parent.$"):
                # 根据JSONPath中的关键字判断使用label还是value
                if "label" in part.lower():
                    result += parent_label
                elif "value" in part.lower():
                    result += parent_value
                else:
                    # 默认使用value
                    result += parent_value
            elif part.startswith("{") and part.endswith("}"):
                placeholder = part[1:-1].strip()
                if placeholder == "parent_value":
                    result += parent_value
                elif placeholder == "parent_label":
                    result += parent_label
            else:
                result += part

        return result

    async def get_cascade_data(
        self,
        config_id: int,
        tenant_id: int
    ) -> List[Dict[str, Any]]:
        config = await FieldCascadeConfig.filter(id=config_id, tenant_id=tenant_id, is_active=True).first()
        if not config:
            return []

        data_records = await FieldCascadeData.filter(
            tenant_id=tenant_id,
            cascade_config_id=config_id
        ).order_by("parent_value").all()

        return [
            {
                "id": record.id,
                "parent_value": record.parent_value,
                "parent_label": record.parent_label,
                "options": record.options,
                "created_at": record.created_at.isoformat() if record.created_at else None
            }
            for record in data_records
        ]


field_cascade_service = FieldCascadeService()
