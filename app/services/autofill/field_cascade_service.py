"""
级联下拉服务 - 处理多级级联下拉的同步和管理
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from jsonpath_ng import parse as jsonpath_parse

from tortoise.expressions import Q

from app.log import logger
from app.models.autofill import (
    FieldCascadeConfig, FieldCascadeData,
    FieldFlattenConfig, FieldSpec, FieldGroupConfig, FieldGroupFieldSpec
)
from app.services.autofill.field_flatten_service import FieldFlattener
from app.services.autofill.field_spec_service import upsert_field_spec
from app.services.agent.core.curl_parser import CurlParser
from app.services.agent.core.api_executor import APIExecutor


class FieldCascadeService:
    """级联下拉服务类"""

    def __init__(self):
        self.api_executor = APIExecutor(timeout=30)
        self.flattener = FieldFlattener()

    async def create_cascade_config(
        self,
        tenant_id: int,
        app_name: str,
        parent_field_id: int,
        parent_field_group_id: int,
        field_name_suffix: str = "-子字段",
        field_label_prefix: str = "",
        api_curl: str = "",
        api_params_mapping: Optional[Dict[str, Any]] = None,
        field_mapping: Optional[Dict[str, Any]] = None,
        enable_flatten: bool = False,
        flatten_config: Optional[Dict[str, Any]] = None,
        is_superuser: bool = False
    ) -> Dict[str, Any]:
        """
        创建级联配置

        Args:
            tenant_id: 租户ID
            app_name: 应用名称
            parent_field_id: 父字段ID
            parent_field_group_id: 父字段组ID
            field_name_suffix: 级联字段后缀
            field_label_prefix: 级联字段标签前缀
            api_curl: 级联API的curl命令
            api_params_mapping: API参数映射
            field_mapping: 字段映射（{label_path, value_path}）
            enable_flatten: 是否启用展平
            flatten_config: 展平配置

        Returns:
            创建结果
        """
        # 获取父字段信息（超级用户可以访问所有租户的字段）
        if is_superuser:
            parent_field = await FieldSpec.filter(id=parent_field_id).first()
            parent_group = await FieldGroupConfig.filter(id=parent_field_group_id).first()
        else:
            parent_field = await FieldSpec.filter(id=parent_field_id, tenant_id=tenant_id).first()
            parent_group = await FieldGroupConfig.filter(id=parent_field_group_id, tenant_id=tenant_id).first()
        
        if not parent_field:
            raise ValueError("父字段不存在")
        
        if not parent_group:
            raise ValueError("父字段组不存在")
        
        # 解析curl
        api_method = "GET"
        api_url = ""
        api_headers = {}
        api_body = ""
        
        if api_curl:
            try:
                parsed = CurlParser.parse(api_curl)
                api_method = parsed.method
                api_url = parsed.url
                api_headers = parsed.headers
                if parsed.body:
                    api_body = parsed.body
            except Exception as e:
                logger.warning(f"解析curl失败: {e}，使用原始值")
        
        # 创建配置
        config = await FieldCascadeConfig.create(
            tenant_id=tenant_id,
            app_name=app_name,
            parent_field_id=parent_field_id,
            parent_field_name=parent_field.field_name,
            parent_field_group_id=parent_field_group_id,
            field_name_suffix=field_name_suffix,
            field_label_prefix=field_label_prefix,
            api_curl=api_curl,
            api_method=api_method,
            api_url=api_url,
            api_headers=api_headers,
            api_body=api_body,
            api_params_mapping=api_params_mapping or {},
            field_mapping=field_mapping or {},
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

    async def update_cascade_config(
        self,
        config_id: int,
        tenant_id: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        更新级联配置

        Args:
            config_id: 配置ID
            tenant_id: 租户ID
            **kwargs: 要更新的字段

        Returns:
            更新结果
        """
        config = await FieldCascadeConfig.filter(id=config_id, tenant_id=tenant_id).first()
        if not config:
            raise ValueError("级联配置不存在")

        # 如果更新了api_curl，重新解析
        if "api_curl" in kwargs and kwargs["api_curl"]:
            try:
                parsed = CurlParser.parse(kwargs["api_curl"])
                kwargs["api_method"] = parsed.method
                kwargs["api_url"] = parsed.url
                kwargs["api_headers"] = parsed.headers
                if parsed.body:
                    kwargs["api_body"] = parsed.body
            except Exception as e:
                logger.warning(f"解析curl失败: {e}")

        # 如果更新了 api_schema，同时更新 api_url 和 api_method（从 Schema 中提取）
        if "api_schema" in kwargs and kwargs["api_schema"]:
            try:
                import tempfile
                import os
                import prance

                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write(kwargs["api_schema"])
                    temp_path = f.name

                try:
                    parser = prance.ResolvingParser(temp_path, backend='openapi-spec-validator')
                    spec = parser.specification

                    # 提取 base_url
                    servers = spec.get('servers', [])
                    base_url = servers[0].get('url', '') if servers else ''

                    # 获取第一个端点
                    paths = spec.get('paths', {})
                    if paths:
                        path, methods = next(iter(paths.items()))
                        method = 'get' if 'get' in methods else 'post'

                        # 更新 api_url 和 api_method
                        kwargs["api_url"] = f"{base_url.rstrip('/')}{path}"
                        kwargs["api_method"] = method.upper()
                finally:
                    os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"解析 api_schema 失败: {e}")

        # 更新配置
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        await config.save()
        
        logger.info(f"[FieldCascadeService] 更新级联配置成功: config_id={config_id}")
        
        return {
            "success": True,
            "cascade_config_id": config_id
        }

    async def get_cascade_configs(
        self,
        tenant_id: int,
        app_name: str,
        parent_field_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取级联配置列表

        Args:
            tenant_id: 租户ID
            app_name: 应用名称
            parent_field_id: 父字段ID（可选）

        Returns:
            配置列表
        """
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
                "field_name_suffix": config.field_name_suffix,
                "field_label_prefix": config.field_label_prefix,
                "api_url": config.api_url,
                "api_params_mapping": config.api_params_mapping,
                "field_mapping": config.field_mapping,
                "enable_flatten": config.enable_flatten,
                "flatten_config": config.flatten_config,
                "last_sync_at": config.last_sync_at.isoformat() if config.last_sync_at else None
            }
            for config in configs
        ]

    async def sync_cascade_fields(
        self,
        config_id: int,
        tenant_id: int,
        is_superuser: bool = False
    ) -> Dict[str, Any]:
        """
        同步级联字段

        Args:
            config_id: 配置ID
            tenant_id: 租户ID

        Returns:
            同步结果
        """
        # 超级用户可以访问所有租户的配置
        if is_superuser:
            config = await FieldCascadeConfig.filter(id=config_id).first()
        else:
            config = await FieldCascadeConfig.filter(id=config_id, tenant_id=tenant_id).first()
        
        if not config:
            raise ValueError("级联配置不存在")
        
        logger.info(f"[FieldCascadeService] 开始同步级联字段: config_id={config_id}")
        
        # 获取父字段（超级用户可以访问所有租户的字段）
        if is_superuser:
            parent_field = await FieldSpec.filter(id=config.parent_field_id).first()
        else:
            parent_field = await FieldSpec.filter(id=config.parent_field_id, tenant_id=tenant_id).first()
        
        if not parent_field:
            raise ValueError("父字段不存在")
        
        # 获取父字段选项
        parent_options = (parent_field.options or {}).get("items", []) if isinstance(parent_field.options, dict) else []
        if not parent_options:
            logger.warning("父字段没有选项")
            return {
                "success": True,
                "message": "父字段没有选项",
                "synced_count": 0
            }
        
        # 同步每个父选项的子字段
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
                    parent_label=parent_label,
                    parent_value=parent_value
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
        
        # 更新同步时间
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
        parent_label: str,
        parent_value: str
    ) -> Dict[str, Any]:
        """
        同步单个级联字段

        Args:
            config: 级联配置
            parent_label: 父选项标签
            parent_value: 父选项值

        Returns:
            同步结果
        """
        logger.info(f"[FieldCascadeService] 同步单个级联字段: parent_label={parent_label}")
        
        # 调用级联API
        api_data = await self._call_cascade_api(
            config=config,
            parent_value=parent_value
        )
        
        if not api_data:
            raise ValueError("API返回数据为空")
        
        # 处理API数据，生成选项
        options = self._extract_options(
            api_data=api_data,
            field_mapping=config.field_mapping,
            enable_flatten=config.enable_flatten,
            flatten_config=config.flatten_config
        )
        
        if not options:
            logger.warning("未提取到选项")
        
        # 生成子字段名称和标签
        child_field_name = f"{config.parent_field_name}_{parent_value}{config.field_name_suffix}"
        child_field_label = f"{config.field_label_prefix or ''}{parent_label}{config.field_name_suffix}"
        
        # 创建或更新子字段
        upsert_result = await upsert_field_spec(
            tenant_id=config.tenant_id,
            app_name=config.app_name,
            field_name=child_field_name,
            field_label=child_field_label,
            field_type="select_single",
            field_group_ids=[config.parent_field_group_id],
            fill_instruction=f"根据'{parent_label}'选择的子项",
            options={"items": options}
        )
        
        # 保存级联数据缓存
        child_field = upsert_result["field_spec"]
        
        await FieldCascadeData.filter(
            cascade_config_id=config.id,
            parent_value=parent_value,
            tenant_id=config.tenant_id
        ).delete()
        
        await FieldCascadeData.create(
            cascade_config_id=config.id,
            parent_value=parent_value,
            tenant_id=config.tenant_id,
            app_name=config.app_name,
            child_field_id=child_field.id,
            child_field_name=child_field_name,
            child_options=options,
            sync_status="success"
        )
        
        logger.info(f"[FieldCascadeService] 单个级联字段同步成功: field_name={child_field_name}")
        
        return {
            "parent_label": parent_label,
            "parent_value": parent_value,
            "success": True,
            "child_field_name": child_field_name,
            "child_field_id": child_field.id,
            "options_count": len(options)
        }

    async def _call_cascade_api(
        self,
        config: FieldCascadeConfig,
        parent_value: str
    ) -> Any:
        """
        调用级联API

        Args:
            config: 级联配置
            parent_value: 父选项值

        Returns:
            API返回数据
        """
        # 优先使用 api_schema 配置
        if config.api_schema:
            return await self._call_cascade_api_from_schema(config, parent_value)

        if not config.api_url:
            raise ValueError("API URL未配置")

        # 构建请求参数
        params = {}

        # 根据api_params_mapping构建参数
        if config.api_params_mapping:
            for param_name, param_config in config.api_params_mapping.items():
                if isinstance(param_config, str):
                    # 简单字符串值
                    if param_config.startswith("{") and param_config.endswith("}"):
                        # 占位符，使用父值
                        params[param_name] = parent_value
                    else:
                        params[param_name] = param_config
                elif isinstance(param_config, dict):
                    # 复杂配置
                    if param_config.get("source") == "parent_value":
                        params[param_name] = parent_value
                    else:
                        params[param_name] = param_config.get("default", "")

        # 解析curl并执行
        try:
            if config.api_curl:
                parsed = CurlParser.parse(config.api_curl)

                # 替换参数
                for key, value in params.items():
                    if key in parsed.query_params:
                        parsed.query_params[key] = value
                    if key in parsed.body_params:
                        parsed.body_params[key] = value

                # 执行API
                result = await self.api_executor.execute(parsed, params)

                if result.success:
                    return result.data
                else:
                    raise ValueError(f"API调用失败: {result.error}")

        except Exception as e:
            logger.error(f"调用级联API失败: {e}")
            raise

        raise ValueError("无法调用API，缺少有效配置")

    async def _call_cascade_api_from_schema(
        self,
        config: FieldCascadeConfig,
        parent_value: str
    ) -> Any:
        """
        根据 OpenAPI Schema 调用级联API

        Args:
            config: 级联配置
            parent_value: 父选项值

        Returns:
            API返回数据
        """
        import tempfile
        import os
        import httpx
        import yaml
        import prance

        try:
            # 1. 解析 OpenAPI Schema
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(config.api_schema)
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
                raise ValueError("Schema中未找到paths配置")

            path, methods = next(iter(paths.items()))
            method = 'get' if 'get' in methods else 'post'
            operation = methods.get(method, {})

            full_url = f"{base_url.rstrip('/')}{path}"

            # 3. 从 x-api-params 获取固定参数和 headers
            x_api_params = operation.get('x-api-params', {})
            headers = x_api_params.get('headers', {}).copy()

            # 4. 构建请求参数（替换 parent_value 占位符）
            params = {k: v for k, v in x_api_params.items() if k != 'headers'}

            # 替换参数中的占位符
            for key, value in params.items():
                if isinstance(value, str) and '{parent_value}' in value:
                    params[key] = value.replace('{parent_value}', parent_value)

            # 5. 发送请求
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
        field_mapping: Dict[str, Any],
        enable_flatten: bool = False,
        flatten_config: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        从API数据中提取选项

        Args:
            api_data: API返回数据
            field_mapping: 字段映射 {label_path, value_path}
            enable_flatten: 是否启用展平
            flatten_config: 展平配置

        Returns:
            选项列表
        """
        if enable_flatten and flatten_config:
            # 使用展平服务
            return self.flattener.flatten_field_options(
                data=api_data,
                flatten_config=flatten_config
            )
        
        # 普通提取方式
        label_path = field_mapping.get("label_path", "$.data[*].label")
        value_path = field_mapping.get("value_path", "$.data[*].value")
        
        try:
            # 使用JSONPath提取
            labels = self._apply_jsonpath(api_data, label_path)
            values = self._apply_jsonpath(api_data, value_path)
            
            # 组合选项
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
        """使用JSONPath提取数据"""
        if not json_path or not data:
            return []
        
        try:
            jsonpath_expr = jsonpath_parse(json_path)
            results = [match.value for match in jsonpath_expr.find(data)]
            return results if results else []
        except Exception as e:
            logger.warning(f"JSONPath解析失败: {e}")
            return []

    async def delete_cascade_config(
        self,
        config_id: int,
        tenant_id: int
    ) -> Dict[str, Any]:
        """
        删除级联配置

        Args:
            config_id: 配置ID
            tenant_id: 租户ID

        Returns:
            删除结果
        """
        config = await FieldCascadeConfig.filter(id=config_id, tenant_id=tenant_id).first()
        if not config:
            raise ValueError("级联配置不存在")
        
        # 删除关联的级联数据
        await FieldCascadeData.filter(cascade_config_id=config_id, tenant_id=tenant_id).delete()
        
        # 软删除配置
        config.is_active = False
        await config.save()
        
        logger.info(f"[FieldCascadeService] 删除级联配置成功: config_id={config_id}")
        
        return {
            "success": True,
            "cascade_config_id": config_id
        }

    async def get_cascade_data(
        self,
        config_id: int,
        tenant_id: int
    ) -> List[Dict[str, Any]]:
        """
        获取级联数据

        Args:
            config_id: 配置ID
            tenant_id: 租户ID

        Returns:
            级联数据列表
        """
        data_list = await FieldCascadeData.filter(
            cascade_config_id=config_id,
            tenant_id=tenant_id
        ).all()
        
        return [
            {
                "parent_value": data.parent_value,
                "child_field_id": data.child_field_id,
                "child_field_name": data.child_field_name,
                "child_options": data.child_options,
                "sync_status": data.sync_status,
                "created_at": data.created_at.isoformat() if data.created_at else None
            }
            for data in data_list
        ]


# 创建服务单例
field_cascade_service = FieldCascadeService()
