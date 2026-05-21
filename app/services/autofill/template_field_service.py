"""
模板类型字段服务
处理模板类型字段的同步和解析
"""
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import yaml
from fastapi import BackgroundTasks
from jsonpath_ng import parse as jsonpath_parse

from app.log import logger
from app.models.autofill import (
    FieldGroupConfig,
    FieldGroupFieldSpec,
    FieldSpec,
    FieldSpecSyncRecord,
    FieldType
)


DEFAULT_TEMPLATE_PARSE_PROMPT = """# 任务：车企售后服务记录模板标准化 + 字段元数据批量提取

## 输出要求
1. 仅输出标准JSON格式，无任何额外文字、解释、标题、分隔线
2. 严格遵守以下JSON结构，不得新增或缺失字段
3. 布尔值使用小写true/false，不得使用字符串"true"/"false"
4. 所有字符串使用双引号包裹，转义内部双引号

## 第一部分：模板标准化规则
1. 保留原文所有固定业务话术、行文逻辑、句式顺序
2. 将所有可变填写内容替换为标准占位符：${field_name}
3. 删除所有人工操作提示、括号内冗余备注、内部指引性文字
4. 保留固定枚举选项的描述，仅将填空位置替换为占位符

## 第二部分：字段提取规则
从原始模板中提取每个可变字段，包含以下属性：
- field_name：字段英文标识（小写下划线，用于占位符和JSON输出）
- field_label：字段中文展示名称
- fill_instruction：整合模板内所有约束信息，包括：字段含义、填写格式、数据类型、可选范围、数值标准、必填要求
- is_required：是否必填，从原文"必填"标注判断，布尔值

## 第三部分：模板填写规则提取
分析模板内容，提取该模板的适用场景和填写规则，包括：
- 该模板适用于什么类型的服务记录场景
- 使用该模板需要满足什么条件
- 模板的主要填写内容和关键信息点
- 模板的使用注意事项

## 输出JSON结构
{
  "standardized_template": "标准化后的完整模板，使用${field_name}占位符",
  "template_rules": "该模板的填写规则和使用指引，包括适用场景、填写要求、注意事项等",
  "fields": [
    {
      "field_name": "customer_name",
      "field_label": "客户姓名",
      "fill_instruction": "填写车主姓名及称呼，文本类型",
      "is_required": true
    }
  ]
}

## 输入模板内容
{template_content}
"""


class TemplateFieldService:
    """模板类型字段服务"""

    async def sync_template_field(
        self,
        field_spec_id: int,
        bg_tasks: BackgroundTasks
    ) -> Dict[str, Any]:
        """
        触发模板字段同步（异步）

        流程：
        1. 验证字段存在且类型为template
        2. 创建同步记录，状态pending
        3. 添加后台任务
        4. 返回同步记录ID
        """
        # 1. 验证字段存在且类型为template
        field_spec = await FieldSpec.get(id=field_spec_id)
        if field_spec.field_type != FieldType.TEMPLATE:
            raise ValueError("仅支持模板类型字段的同步")

        # 2. 创建同步记录
        sync_record = await FieldSpecSyncRecord.create(
            field_spec_id=field_spec_id,
            tenant_id=field_spec.tenant_id,
            app_name=field_spec.app_name,
            status="pending"
        )

        # 3. 添加后台任务
        bg_tasks.add_task(self._do_sync, sync_record.id, field_spec_id)

        # 4. 立即返回
        return {
            "sync_record_id": sync_record.id,
            "status": "pending",
            "message": "同步任务已提交"
        }

    async def _do_sync(
        self,
        sync_record_id: int,
        field_spec_id: int
    ) -> None:
        """
        执行同步（后台任务）

        流程：
        1. 更新同步记录状态为processing
        2. 获取字段配置（template_config）
        3. 解析curl，发起请求获取模板列表
        4. 遍历模板列表，处理每个模板
        5. 更新同步记录状态为completed或failed
        """
        logger.info(f"[TemplateFieldService] 开始同步字段 {field_spec_id}")

        # 1. 更新状态为processing
        await self._update_sync_status(sync_record_id, "processing")

        try:
            # 2. 获取字段配置
            field_spec = await FieldSpec.get(id=field_spec_id)

            # 从YAML配置(api_schema)中解析模板配置
            api_schema_yaml = field_spec.options.get("api_schema", "")
            if not api_schema_yaml:
                raise ValueError("字段缺少api_schema配置")

            template_config = self._parse_template_config_from_yaml(api_schema_yaml)

            if not template_config:
                raise ValueError("无法从api_schema解析模板配置")

            # 3. 获取模板列表
            templates = await self._fetch_templates_from_schema(api_schema_yaml)

            if not templates:
                logger.warning(f"[TemplateFieldService] 未获取到模板列表")
                await self._update_sync_status(
                    sync_record_id,
                    "completed",
                    total_count=0,
                    success_count=0,
                    failed_count=0,
                    details=[]
                )
                return

            # 4. 遍历处理每个模板
            results = []
            template_rules_map = {}  # 存储模板ID到填写规则的映射

            for template in templates:
                try:
                    result = await self._process_single_template(
                        template,
                        template_config,
                        field_spec
                    )
                    results.append(result)
                    # 收集模板填写规则
                    if result.get("success") and result.get("template_id"):
                        template_rules_map[result["template_id"]] = result.get("template_rules", "")
                except Exception as e:
                    import traceback
                    logger.error(f"[TemplateFieldService] 处理模板失败: {e}")
                    logger.error(f"[TemplateFieldService] 堆栈跟踪: {traceback.format_exc()}")
                    results.append({
                        "success": False,
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    })

            # 5. 创建模板选择下拉字段（如果配置了）
            await self._create_template_selector_field(
                field_spec,
                template_config,
                templates,
                template_rules_map
            )

            # 6. 更新状态为completed
            success_count = len([r for r in results if r.get("success")])
            await self._update_sync_status(
                sync_record_id,
                "completed",
                total_count=len(templates),
                success_count=success_count,
                failed_count=len(templates) - success_count,
                details=results
            )

            logger.info(f"[TemplateFieldService] 同步完成: 成功 {success_count}/{len(templates)}")

        except Exception as e:
            logger.error(f"[TemplateFieldService] 同步失败: {e}")
            # 7. 更新状态为failed
            await self._update_sync_status(
                sync_record_id,
                "failed",
                error_msg=str(e)
            )

    async def _process_single_template(
        self,
        template: Dict,
        template_config: Dict,
        field_spec: FieldSpec
    ) -> Dict[str, Any]:
        """处理单个模板"""
        # 4.1 提取模板名称和内容
        template_name_path = template_config.get("template_name_path", "$.name")
        template_content_path = template_config.get("template_content_path", "$.template_content")
        template_id_path = template_config.get("template_id_path", "$.id")

        template_name = self._extract_by_jsonpath(template, template_name_path)
        template_content = self._extract_by_jsonpath(template, template_content_path)
        template_id = self._extract_by_jsonpath(template, template_id_path)

        if not template_name:
            logger.error(f"[TemplateFieldService] 无法提取模板名称，路径: {template_name_path}, 可用字段: {list(template.keys())}")
            raise ValueError(f"无法提取模板名称，路径 '{template_name_path}' 无效")
        if not template_content:
            logger.error(f"[TemplateFieldService] 无法提取模板内容，路径: {template_content_path}, 可用字段: {list(template.keys())}")
            raise ValueError(f"无法提取模板内容，路径 '{template_content_path}' 无效")

        logger.info(f"[TemplateFieldService] 处理模板: {template_name}")

        # 4.2 使用LLM解析 - 使用json_parser方法
        parse_prompt = field_spec.options.get("parse_prompt") or template_config.get("parse_prompt") or DEFAULT_TEMPLATE_PARSE_PROMPT

        parsed = await self._parse_template_with_llm(template_content, parse_prompt, template_name)

        # 4.3 生成字段组名称
        group_name_pattern = template_config.get(
            "group_name_pattern",
            "$.name + 服务记录"
        )
        group_name = self._generate_group_name(
            group_name_pattern,
            template
        )

        # 4.4 获取字段组信息
        relations = await FieldGroupFieldSpec.filter(
            field_spec_id=field_spec.id
        ).all()

        if not relations:
            raise ValueError("字段未关联字段组")

        # 4.5 创建字段组和字段
        from app.services.autofill.field_group_service import FieldGroupService
        field_group_service = FieldGroupService()

        # 转换字段格式，所有字段类型默认为text
        fields_for_group = []
        logger.info(f"[TemplateFieldService] 开始处理字段，共 {len(parsed.get('fields', []))} 个")
        for field in parsed.get("fields", []):
            # 支持 field_name/name 和 field_label/label 两种字段名格式
            field_name = field.get("field_name") or field.get("name")
            field_label = field.get("field_label") or field.get("label")
            logger.info(f"[TemplateFieldService] 处理字段: field_name={field_name}, field_label={field_label}, field={field}")

            if not field_name or not field_label:
                logger.warning(f"[TemplateFieldService] 跳过无效字段: {field}")
                continue

            field_data = {
                "field_name": field_name,
                "field_label": field_label,
                "field_type": "text",  # 强制默认为text
                "fill_instruction": field.get("fill_instruction", f"请填写{field_label}"),
                "options": {}
            }
            fields_for_group.append(field_data)

        # 构建output_templates，包含标准化模板和原始模板
        output_templates = {
            "default": {
                "template": parsed["standardized_template"],
                "description": "标准化后的模板"
            },
            "original": {
                "template": template_content,
                "description": "原始模板内容"
            }
        }

        await field_group_service.upsert_field_group(
            tenant_id=field_spec.tenant_id,
            app_name=field_spec.app_name,
            group_name=group_name,
            output_templates=output_templates,
            fields=fields_for_group
        )

        return {
            "success": True,
            "template_name": template_name,
            "template_id": template_id,
            "group_name": group_name,
            "fields_count": len(parsed.get("fields", [])),
            "template_rules": parsed.get("template_rules", "")
        }

    async def _create_template_selector_field(
        self,
        field_spec: FieldSpec,
        template_config: Dict,
        templates: List[Dict],
        template_rules_map: Dict[str, str] = None
    ) -> None:
        """
        创建模板选择下拉字段

        根据配置生成一个下拉选择字段，用于选择模板
        """
        # 检查是否配置了模板选择器字段
        selector_config = template_config.get("template_selector", {})
        if not selector_config.get("enabled", False):
            return

        selector_field_name = selector_config.get("field_name", "template_selector")
        selector_field_label = selector_config.get("field_label", "模板选择")
        label_path = selector_config.get("label_path", "$.name")
        value_path = selector_config.get("value_path", "$.id")

        # 构建选项列表
        items = []
        for template in templates:
            label = self._extract_by_jsonpath(template, label_path)
            value = self._extract_by_jsonpath(template, value_path)
            if label and value:
                # 获取该模板的填写规则
                fill_instruction = ""
                if template_rules_map and value in template_rules_map:
                    fill_instruction = template_rules_map[value]
                
                items.append({
                    "label": str(label),
                    "value": str(value),
                    "is_deleted": False,
                    "fill_instruction": fill_instruction
                })

        if not items:
            logger.warning("[TemplateFieldService] 没有可用的模板选项")
            return

        # 获取字段组信息
        relations = await FieldGroupFieldSpec.filter(
            field_spec_id=field_spec.id
        ).all()

        if not relations:
            logger.warning("[TemplateFieldService] 字段未关联字段组，无法创建模板选择器")
            return

        # 创建下拉选择字段
        from app.services.autofill.field_spec_service import upsert_field_spec

        result = await upsert_field_spec(
            tenant_id=field_spec.tenant_id,
            app_name=field_spec.app_name,
            field_name=selector_field_name,
            field_label=selector_field_label,
            field_type=FieldType.SELECT_SINGLE,
            fill_instruction="请选择适用的模板",
            options={"items": items}
        )

        # 创建字段组与字段的关联关系
        field_group_id = relations[0].field_group_id
        existing_relation = await FieldGroupFieldSpec.filter(
            field_group_id=field_group_id,
            field_spec_id=result["field_spec"].id
        ).first()
        if not existing_relation:
            await FieldGroupFieldSpec.create(
                field_group_id=field_group_id,
                field_spec_id=result["field_spec"].id,
                tenant_id=field_spec.tenant_id,
                app_name=field_spec.app_name
            )

        logger.info(f"[TemplateFieldService] 创建模板选择器字段成功: {selector_field_name}, 选项数: {len(items)}")

    async def _fetch_templates_from_schema(
        self,
        api_schema_yaml: str
    ) -> List[Dict]:
        """
        根据OpenAPI Schema配置获取外部模板列表
        复用FieldCascadeService中的API调用逻辑
        """
        try:
            # 使用 yaml.safe_load 直接解析，不进行 OpenAPI 规范验证
            spec = yaml.safe_load(api_schema_yaml)
            if not spec or not isinstance(spec, dict):
                raise ValueError("无效的 YAML 格式")

            servers = spec.get('servers', [])
            base_url = servers[0].get('url', '') if servers else ''

            paths = spec.get('paths', {})
            if not paths:
                raise ValueError("Schema中未找到paths配置")

            path, methods = next(iter(paths.items()))
            method = 'get' if 'get' in methods else 'post'
            operation = methods.get(method, {})

            full_url = f"{base_url.rstrip('/')}{path}"

            # 获取x-api-params配置
            x_api_params = operation.get('x-api-params', {})
            headers = x_api_params.get('headers', {}).copy()
            params = {k: v for k, v in x_api_params.items() if k != 'headers'}

            logger.info(f"[TemplateFieldService] 请求模板列表: {method.upper()} {full_url}")

            # 发起HTTP请求
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == 'get':
                    response = await client.get(full_url, headers=headers, params=params)
                else:
                    headers.setdefault('Content-Type', 'application/json')
                    response = await client.post(full_url, headers=headers, json=params)

                response.raise_for_status()
                data = response.json()

            # 从x-template-mapping中获取模板列表路径
            template_mapping = operation.get('x-template-mapping', {})
            template_list_path = template_mapping.get('template_list_path', '$.data[*]')

            templates = self._extract_by_jsonpath(data, template_list_path)

            if templates is None:
                # 回退到默认逻辑
                if isinstance(data, list):
                    templates = data
                elif isinstance(data, dict) and "data" in data:
                    templates = data["data"]
                else:
                    templates = [data]

            # 确保返回的是列表
            if not isinstance(templates, list):
                templates = [templates]

            logger.info(f"[TemplateFieldService] 提取到 {len(templates)} 个模板")
            return templates

        except Exception as e:
            logger.error(f"[TemplateFieldService] 获取模板列表失败: {e}")
            raise ValueError(f"获取模板列表失败: {str(e)}")

    async def _parse_template_with_llm(
        self,
        template_content: str,
        parse_prompt: str,
        template_name: str = ""
    ) -> Dict[str, Any]:
        """
        使用LLM解析模板内容 - 使用json_parser方法

        返回: {
            "standardized_template": "标准化后的模板",
            "template_rule": "模板应用规则",
            "fields": [
                {"field_name": "contact_phone", "field_label": "联系电话", "is_required": true},
                ...
            ]
        }
        """
        from app.services.llm.llm_config_service import llm_config_service
        from app.services.llm.llm_proxy_service import llm_proxy_service

        # 1. 获取默认LLM配置
        config = await llm_config_service.get_default_config()
        if not config:
            raise ValueError("未找到默认LLM配置，请先配置LLM模型")

        # 2. 构建完整prompt
        # 使用 replace 而不是 format，避免提示词中的 {field_name} 等占位符被误解析
        full_prompt = parse_prompt.replace("{template_content}", template_content)

        logger.info(f"[TemplateFieldService] 调用LLM解析模板，模型: {config.name}")

        # 3. 调用LLM服务 - 使用json_parser方法
        result = await llm_proxy_service.process_request(
            query=full_prompt,
            tools=[],  # json_parser方法不需要tools
            system_prompt="你是一个专业的模板解析助手，擅长从非标准模板中提取结构化信息。",
            method="json_parser",  # 使用json_parser方法直接返回JSON
            config=config
        )

        if not result.get("success"):
            error_msg = result.get("error", "未知错误")
            logger.error(f"[TemplateFieldService] LLM调用失败: {error_msg}")
            raise ValueError(f"LLM解析失败: {error_msg}")

        # 4. 解析JSON响应
        try:
            parsed = result.get("data", {})

            if isinstance(parsed, str):
                # 如果返回的是字符串，尝试解析JSON
                parsed = json.loads(parsed)

            # 5. 验证返回格式
            if "standardized_template" not in parsed or "fields" not in parsed:
                logger.error(f"[TemplateFieldService] LLM返回格式不正确: {parsed}")
                raise ValueError("LLM返回格式不正确，缺少standardized_template或fields")

            # 6. 验证字段格式并转换
            fields = []
            for field in parsed.get("fields", []):
                field_name = field.get("field_name") or field.get("name")
                field_label = field.get("field_label") or field.get("label")
                is_required = field.get("is_required", False)
                fill_instruction = field.get("fill_instruction", "")

                if not field_name or not field_label:
                    logger.warning(f"[TemplateFieldService] 字段缺少名称或标签: {field}")
                    continue

                # 构建字段数据，所有字段类型默认为text
                field_data = {
                    "field_name": field_name,
                    "field_label": field_label,
                    "is_required": is_required,
                    "fill_instruction": fill_instruction or f"请填写{field_label}"
                }
                fields.append(field_data)

            logger.info(f"[TemplateFieldService] LLM解析成功，提取 {len(fields)} 个字段")

            return {
                "standardized_template": parsed.get("standardized_template", ""),
                "fields": fields
            }

        except json.JSONDecodeError as e:
            logger.error(f"[TemplateFieldService] LLM返回内容不是有效的JSON: {e}, 内容: {result.get('data')}")
            raise ValueError(f"LLM返回内容不是有效的JSON: {e}")
        except Exception as e:
            logger.error(f"[TemplateFieldService] 解析LLM响应失败: {e}")
            raise ValueError(f"解析LLM响应失败: {e}")

    def _generate_group_name(
        self,
        pattern: str,
        template_data: Dict
    ) -> str:
        """
        根据规则生成字段组名称

        格式: $.data[*].name + 的服务记录
        - $.data[*].name: JSONPath表达式，从API响应数据中提取模板名称
        - +: 分隔符
        - 的服务记录: 固定后缀
        """
        try:
            # 解析pattern，分离jsonpath部分和固定文本部分
            if "+" in pattern:
                jsonpath_part, suffix = pattern.rsplit("+", 1)
                jsonpath_part = jsonpath_part.strip()
                suffix = suffix.strip()
            else:
                jsonpath_part = pattern.strip()
                suffix = ""

            # 使用jsonpath提取值
            jsonpath_expr = jsonpath_parse(jsonpath_part)
            matches = jsonpath_expr.find(template_data)

            if matches:
                template_name = matches[0].value
                return f"{template_name}{suffix}".strip()

            # 如果JSONPath提取失败，尝试直接使用name字段
            if "name" in template_data:
                return f"{template_data['name']}{suffix}".strip()

            return f"未命名{suffix}".strip()
        except Exception as e:
            logger.warning(f"[TemplateFieldService] 生成字段组名称失败: {e}")
            # 尝试使用默认模板名
            if "name" in template_data:
                return f"{template_data['name']} 服务记录"
            return "未命名字段组"

    def _extract_by_jsonpath(
        self,
        data: Dict,
        jsonpath: str
    ) -> Any:
        """使用JSONPath从数据中提取值

        如果JSONPath包含 [*] 通配符，返回所有匹配项的列表
        否则返回第一个匹配项的值
        """
        if not jsonpath or not data:
            return None

        try:
            jsonpath_expr = jsonpath_parse(jsonpath)
            matches = jsonpath_expr.find(data)

            if not matches:
                return None

            # 如果JSONPath包含 [*] 或类似通配符，返回所有匹配项
            if '[*]' in jsonpath or '.*' in jsonpath:
                return [match.value for match in matches]

            # 否则返回第一个匹配项
            return matches[0].value
        except Exception as e:
            logger.warning(f"[TemplateFieldService] JSONPath提取失败: {e}")
            return None

    def _parse_template_config_from_yaml(self, api_schema_yaml: str) -> Optional[Dict[str, Any]]:
        """
        从YAML格式的api_schema中解析模板配置

        返回: {
            "template_name_path": "...",
            "template_content_path": "...",
            "template_id_path": "...",
            "group_name_pattern": "...",
            "parse_prompt": "...",
            "template_list_path": "...",
            "template_selector": {...}
        }
        """
        try:
            schema = yaml.safe_load(api_schema_yaml)

            if not schema or 'paths' not in schema:
                return None

            # 获取第一个路径的第一个方法
            for path, methods in schema['paths'].items():
                for method, operation in methods.items():
                    if not isinstance(operation, dict):
                        continue

                    # 获取 x-template-mapping 配置
                    template_mapping = operation.get('x-template-mapping', {})

                    # 获取模板选择器配置
                    template_selector = template_mapping.get('template_selector', {})

                    return {
                        "template_list_path": template_mapping.get('template_list_path', '$.data[*]'),
                        "template_name_path": template_mapping.get('template_name_path', '$.name'),
                        "template_content_path": template_mapping.get('template_content_path', '$.template_content'),
                        "template_id_path": template_mapping.get('template_id_path', '$.id'),
                        "group_name_pattern": template_mapping.get('group_name_pattern', '$.name + 服务记录'),
                        "parse_prompt": template_mapping.get('parse_prompt', DEFAULT_TEMPLATE_PARSE_PROMPT),
                        "template_selector": template_selector
                    }

            return None
        except Exception as e:
            logger.error(f"[TemplateFieldService] 解析YAML配置失败: {e}")
            return None

    async def _update_sync_status(
        self,
        sync_record_id: int,
        status: str,
        total_count: int = 0,
        success_count: int = 0,
        failed_count: int = 0,
        error_msg: str = "",
        details: Optional[List[Dict]] = None
    ) -> None:
        """更新同步记录状态"""
        sync_record = await FieldSpecSyncRecord.get(id=sync_record_id)
        sync_record.status = status
        sync_record.total_count = total_count
        sync_record.success_count = success_count
        sync_record.failed_count = failed_count
        sync_record.error_msg = error_msg
        if details:
            sync_record.details = details
        await sync_record.save()

    async def get_sync_status(
        self,
        sync_record_id: int
    ) -> Dict[str, Any]:
        """查询同步状态"""
        sync_record = await FieldSpecSyncRecord.get(id=sync_record_id)

        return {
            "sync_record_id": sync_record.id,
            "field_spec_id": sync_record.field_spec_id,
            "status": sync_record.status,
            "total_count": sync_record.total_count,
            "success_count": sync_record.success_count,
            "failed_count": sync_record.failed_count,
            "error_msg": sync_record.error_msg,
            "details": sync_record.details,
            "created_at": sync_record.created_at.isoformat() if sync_record.created_at else "",
            "updated_at": sync_record.updated_at.isoformat() if sync_record.updated_at else ""
        }


template_field_service = TemplateFieldService()
