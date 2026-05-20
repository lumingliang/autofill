"""
模板类型字段服务
处理模板类型字段的同步和解析
"""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import BackgroundTasks

from app.log import logger
from app.models.autofill import (
    FieldGroupConfig,
    FieldGroupFieldSpec,
    FieldSpec,
    FieldSpecSyncRecord,
    FieldType,
    FillPage
)
from app.services.autofill.field_cascade_service import FieldCascadeService


DEFAULT_TEMPLATE_PARSE_PROMPT = """你是一个专业的模板解析助手。请分析以下模板内容，提取关键信息字段并识别模板应用规则。

## 输入模板内容
{template_content}

## 解析要求
1. 分析模板内容，识别所有需要填写的关键信息点
2. 为每个关键信息提取字段：
   - field_name: 字段英文名（小写，下划线连接，如：customer_name）
   - field_label: 字段中文标签（清晰易懂的中文名称）
   - fill_instruction: 填写指引（从模板中提取的约束信息）

## fill_instruction 填写指引提取规范
fill_instruction 必须整合模板中该字段的所有约束信息，包括但不限于：
1. **字段含义**：该字段代表什么业务含义
2. **填写格式**：如日期格式(YYYY-MM-DD)、手机号格式(11位)、身份证号格式(18位)等
3. **数据类型**：如字符串、数字、日期、布尔值等
4. **可选范围**：如是/否选项、特定枚举值（如：高中低、优良好差）
5. **数值标准**：如最小值、最大值、精度要求、单位（元/千克/公里等）
6. **必填要求**：是否必须填写
7. **示例值**：从模板中提取的具体示例
8. **特殊规则**：如只能输入数字、不能包含特殊字符、长度限制等

## 应用规则分析
分析并总结该模板的适用场景和触发条件，即：
- 什么情况下应该使用这个模板？
- 哪些业务场景或条件满足时需要应用本模板？
- 模板的使用限制或前置条件是什么？

## 输出格式（JSON）
你必须严格按照以下JSON格式返回，不要添加任何其他内容：

{
    "template_content": "原始模板内容，将其中的动态信息替换为 ${field_name} 格式的变量引用",
    "apply_rules": "描述该模板的应用规则和适用场景，例如：适用于个人客户的道路救援服务申请，当客户类型为个人且服务类型为道路救援时使用本模板",
    "fields": [
        {"field_name": "customer_name", "field_label": "车主姓名", "fill_instruction": "客户姓名，字符串类型，如：张先生、李女士。必填。"},
        {"field_name": "contact_phone", "field_label": "联系电话", "fill_instruction": "客户联系电话，11位手机号码，数字格式。必填。"},
        {"field_name": "service_type", "field_label": "服务类型", "fill_instruction": "服务类型，如：道路救援、保养预约、维修服务。必填。"}
    ]
}

## 重要说明
1. template_content 是原始模板内容，将识别到的动态信息替换为 ${field_name} 格式，保持模板主体内容不变
2. apply_rules 必须清晰描述模板的应用场景和条件
3. 字段名使用英文小写，下划线连接
4. 字段标签使用中文，清晰易懂
5. **fill_instruction 必须全面**：整合字段含义、格式、类型、范围、标准、必填要求等所有约束信息
6. 只返回JSON，不要包含任何解释说明
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
        5. 创建模板选择下拉字段
        6. 更新同步记录状态为completed或failed
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
            templates = await self._fetch_templates(template_config)

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

            # 4. 遍历处理每个模板，收集模板信息
            results = []
            template_info_list = []  # 收集模板信息用于创建下拉字段
            
            for template in templates:
                try:
                    result = await self._process_single_template(
                        template,
                        template_config,
                        field_spec
                    )
                    results.append(result)
                    
                    # 收集模板信息
                    template_name_field = template_config.get("template_name_field", "name")
                    template_name = template.get(template_name_field, "")
                    template_id = template.get("id", template.get("id", str(id(template))))
                    
                    template_info_list.append({
                        "template_id": template_id,
                        "template_name": template_name,
                        "apply_rules": result.get("apply_rules", "")
                    })
                except Exception as e:
                    logger.error(f"[TemplateFieldService] 处理模板失败: {e}")
                    results.append({
                        "success": False,
                        "error": str(e)
                    })

            # 5. 创建模板选择下拉字段
            await self._create_template_selector_field(
                field_spec=field_spec,
                template_config=template_config,
                templates=template_info_list
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
            # 6. 更新状态为failed
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
        # 使用字段名直接从模板字典中提取
        template_name_field = template_config.get("template_name_field", "name")
        template_content_field = template_config.get("template_content_field", "template_content")

        template_name = template.get(template_name_field)
        original_template_content = template.get(template_content_field)

        if not template_name:
            logger.error(f"[TemplateFieldService] 无法提取模板名称，字段: {template_name_field}, 可用字段: {list(template.keys())}")
            raise ValueError(f"无法提取模板名称，字段 '{template_name_field}' 不存在")
        if not original_template_content:
            logger.error(f"[TemplateFieldService] 无法提取模板内容，字段: {template_content_field}, 可用字段: {list(template.keys())}")
            raise ValueError(f"无法提取模板内容，字段 '{template_content_field}' 不存在")

        logger.info(f"[TemplateFieldService] 处理模板: {template_name}")

        # 4.2 使用LLM解析
        # 直接将原始模板内容传给大模型，让大模型自己解析
        # 优先使用字段的自定义提示词，其次使用模板配置中的提示词，最后使用默认提示词
        parse_prompt = field_spec.options.get("parse_prompt") or template_config.get("parse_prompt") or DEFAULT_TEMPLATE_PARSE_PROMPT

        parsed = await self._parse_template_with_llm(original_template_content, parse_prompt)

        # 4.3 生成字段组名称
        group_name_pattern = template_config.get(
            "group_name_pattern",
            "{template_name} 服务记录"
        )
        group_name = await self._generate_group_name(
            group_name_pattern,
            {"template_name": template_name},
            template  # 传递完整模板数据以支持 $.parent 语法
        )

        # 4.4 获取页面信息
        relations = await FieldGroupFieldSpec.filter(
            field_spec_id=field_spec.id
        ).all()

        if not relations:
            raise ValueError("字段未关联字段组")

        field_group = await FieldGroupConfig.get(id=relations[0].field_group_id)
        page = await FillPage.get(id=field_group.page_id)

        # 4.5 创建字段组和字段
        # 延迟导入避免循环依赖
        from app.services.autofill.field_group_service import FieldGroupService
        field_group_service = FieldGroupService()

        # 转换字段格式，field_type直接设为text
        fields_for_group = []
        for field in parsed["fields"]:
            field_data = {
                "field_name": field["field_name"],
                "field_label": field["field_label"],
                "field_type": "text",  # 直接设为text，不再从LLM获取
                "fill_instruction": field.get("fill_instruction", f"请填写{field['field_label']}"),
                "options": field.get("options", {})
            }
            fields_for_group.append(field_data)

        # 构建output_templates：包含default模板和原始模板
        output_templates = {
            "default": {"template": parsed.get("template_content", "")},
            "original": {"template": original_template_content, "description": "原始模板内容"}
        }

        # 如果有apply_rules，也保存起来
        apply_rules = parsed.get("apply_rules", "")
        if apply_rules:
            output_templates["apply_rules"] = {"template": apply_rules, "description": "模板应用规则"}

        await field_group_service.upsert_field_group(
            tenant_id=field_spec.tenant_id,
            app_name=field_spec.app_name,
            page_name=page.page_name,
            group_name=group_name,
            output_templates=output_templates,
            fields=fields_for_group
        )

        return {
            "success": True,
            "template_name": template_name,
            "group_name": group_name,
            "fields_count": len(parsed.get("fields", [])),
            "apply_rules": apply_rules
        }

    async def _create_template_selector_field(
        self,
        field_spec: FieldSpec,
        template_config: Dict,
        templates: List[Dict]
    ) -> None:
        """
        创建模板选择下拉字段

        字段选项包含：
        - label: 模板名称
        - value: 模板ID
        - description: 模板应用规则（填写指引）
        
        支持通过配置指定 label_path 和 value_path 的 JSONPath
        """
        from app.services.autofill.field_spec_service import upsert_field_spec

        # 获取关联的字段组
        relations = await FieldGroupFieldSpec.filter(
            field_spec_id=field_spec.id
        ).all()
        
        if not relations:
            logger.warning("[TemplateFieldService] 模板字段未关联字段组，跳过创建模板选择字段")
            return

        field_group_ids = [r.field_group_id for r in relations]

        # 构建下拉选项
        options = []
        for template in templates:
            options.append({
                "label": template.get("template_name", ""),
                "value": str(template.get("template_id", "")),
                "fill_instruction": template.get("apply_rules", ""),
                "is_deleted": False
            })

        # 从配置中获取字段名称和标签
        selector_field_name = template_config.get("selector_field_name", "template_selector")
        selector_field_label = template_config.get("selector_field_label", "选择模板")

        # 创建或更新模板选择下拉字段
        await upsert_field_spec(
            tenant_id=field_spec.tenant_id,
            app_name=field_spec.app_name,
            field_name=selector_field_name,
            field_label=selector_field_label,
            field_type=FieldType.SELECT_SINGLE,
            field_group_ids=field_group_ids,
            fill_instruction="请选择要使用的模板，每个模板有对应的应用规则，请根据实际业务场景选择合适的模板",
            options={
                "items": options,
                "label_path": template_config.get("label_path", "$.data[*].templateName"),
                "value_path": template_config.get("value_path", "$.data[*].id")
            }
        )

        logger.info(f"[TemplateFieldService] 创建模板选择字段成功: {selector_field_name}")

    async def _fetch_templates(
        self,
        template_config: Dict
    ) -> List[Dict]:
        """
        根据API配置获取外部模板列表（复用FieldCascadeService的HTTP请求逻辑）
        """
        url = template_config.get("url", "")
        method = template_config.get("method", "GET")
        headers = template_config.get("headers", {})
        body = template_config.get("body")

        if not url:
            raise ValueError("缺少URL配置")

        logger.info(f"[TemplateFieldService] 请求模板列表: {method} {url}")

        # 发起HTTP请求
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=body)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")

            response.raise_for_status()
            data = response.json()

        # 使用template_list_path提取模板列表（复用FieldCascadeService._apply_jsonpath）
        template_list_path = template_config.get("template_list_path", "$.data[*]")
        templates = FieldCascadeService._apply_jsonpath(data, template_list_path)

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

    async def _parse_template_with_llm(
        self,
        template_content: str,
        parse_prompt: str
    ) -> Dict[str, Any]:
        """
        使用LLM解析模板内容（使用json_parser方法自动处理JSON解析）

        返回: {
            "template_content": "带变量引用的模板内容",
            "apply_rules": "模板应用规则",
            "fields": [
                {"field_name": "contact_phone", "field_label": "联系电话", "fill_instruction": "..."},
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

        # 2. 构建完整prompt - 将原始模板内容附加到prompt后面
        full_prompt = f"{parse_prompt}\n\n## 输入模板内容\n{template_content}"

        logger.info(f"[TemplateFieldService] 调用LLM解析模板，模型: {config.name}")

        # 3. 调用LLM服务（使用json_parser方法自动处理JSON解析）
        result = await llm_proxy_service.process_request(
            query=full_prompt,
            tools=[],
            system_prompt="你是一个专业的模板解析助手，擅长从非标准模板中提取结构化信息。",
            method="json_parser",  # 使用json_parser方法，自动处理JSON解析
            config=config,
            full_system_prompt=full_prompt
        )

        if not result.get("success"):
            error_msg = result.get("error", "未知错误")
            logger.error(f"[TemplateFieldService] LLM调用失败: {error_msg}")
            raise ValueError(f"LLM解析失败: {error_msg}")

        # 4. 获取解析结果（json_parser方法直接返回解析后的字典）
        parsed = result.get("data", {})

        # 5. 验证返回格式
        if not isinstance(parsed, dict):
            logger.error(f"[TemplateFieldService] LLM返回不是字典类型: {type(parsed)}")
            raise ValueError("LLM返回格式不正确，期望JSON对象")

        if "template_content" not in parsed or "fields" not in parsed:
            logger.error(f"[TemplateFieldService] LLM返回格式不正确，缺少必要字段: {parsed.keys()}")
            raise ValueError("LLM返回格式不正确，缺少template_content或fields")

        # 6. 验证字段格式并转换（field_type直接设为text，不再从LLM获取）
        fields = []
        for field in parsed.get("fields", []):
            field_name = field.get("field_name") or field.get("name")
            field_label = field.get("field_label") or field.get("label")
            fill_instruction = field.get("fill_instruction") or field.get("field_guide") or field.get("guide") or field.get("description")

            if not field_name or not field_label:
                logger.warning(f"[TemplateFieldService] 字段缺少名称或标签: {field}")
                continue

            # field_type直接设为text，不再从LLM获取
            field_data = {
                "field_name": field_name,
                "field_label": field_label,
                "field_type": "text",
                "fill_instruction": fill_instruction or f"请填写{field_label}"
            }
            fields.append(field_data)

        logger.info(f"[TemplateFieldService] LLM解析成功，提取 {len(fields)} 个字段")

        # 直接使用LLM返回的template_content，不再做格式处理
        template_content_result = parsed.get("template_content", "")
        apply_rules = parsed.get("apply_rules", "")

        return {
            "template_content": template_content_result,
            "apply_rules": apply_rules,
            "fields": fields
        }

    async def _generate_group_name(
        self,
        pattern: str,
        template_data: Dict,
        parent_template: Dict = None
    ) -> str:
        """
        根据规则生成字段组名称（复用FieldCascadeService._apply_jsonpath）

        格式: $.data[*].name + 的服务记录
        - $.data[*].name: JSONPath表达式，从API响应数据中提取模板名称
        - +: 分隔符
        - 的服务记录: 固定后缀

        参数:
        - pattern: 命名规则模板，使用 JSONPath 格式
        - template_data: 包含 template_name 的字典（备用）
        - parent_template: 完整的模板数据，用于 JSONPath 提取
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

            # 确定数据源 - 使用完整的模板数据进行 JSONPath 提取
            data_to_search = parent_template if parent_template else template_data

            # 复用FieldCascadeService._apply_jsonpath方法
            matches = FieldCascadeService._apply_jsonpath(data_to_search, jsonpath_part)

            if matches:
                template_name = matches[0]
                return f"{template_name}{suffix}".strip()

            # 如果JSONPath提取失败，使用默认的 template_name
            if "template_name" in template_data:
                return f"{template_data['template_name']}{suffix}".strip()

            return f"未命名{suffix}".strip()
        except Exception as e:
            logger.warning(f"[TemplateFieldService] 生成字段组名称失败: {e}")
            # 尝试使用默认模板名
            if "template_name" in template_data:
                return f"{template_data['template_name']} 服务记录"
            return "未命名字段组"

    def _parse_template_config_from_yaml(self, api_schema_yaml: str) -> Optional[Dict[str, Any]]:
        """
        从YAML格式的api_schema中解析模板配置（复用FieldCascadeService的yaml解析逻辑）

        返回: {
            "api_schema": "原始yaml字符串",
            "url": "完整URL",
            "method": "GET/POST",
            "headers": {...},
            "body": {...},
            "template_list_path": "...",
            "template_name_field": "...",
            "template_content_field": "...",
            "group_name_pattern": "...",
            "parse_prompt": "..."
        }
        """
        try:
            import tempfile
            import prance

            # 复用FieldCascadeService._call_cascade_api_from_schema中的yaml解析逻辑
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(api_schema_yaml)
                temp_path = f.name

            try:
                parser = prance.ResolvingParser(temp_path, backend='openapi-spec-validator')
                spec = parser.specification
            finally:
                import os
                os.unlink(temp_path)

            servers = spec.get('servers', [])
            base_url = servers[0].get('url', '') if servers else ''

            if not base_url:
                base_url = 'http://localhost:3200'

            paths = spec.get('paths', {})
            if not paths:
                return None

            for path, methods in paths.items():
                for method, operation in methods.items():
                    if not isinstance(operation, dict):
                        continue

                    # 获取 x-template-mapping 配置
                    template_mapping = operation.get('x-template-mapping', {})

                    # 获取 x-api-params 配置（包含headers等）
                    api_params = operation.get('x-api-params', {})

                    # 构建URL
                    full_url = f"{base_url.rstrip('/')}{path}"

                    # 提取headers
                    headers = {}
                    for key, value in api_params.get('headers', {}).items():
                        headers[key] = value

                    # 提取body
                    body = None
                    if 'requestBody' in operation:
                        body_content = operation['requestBody'].get('content', {})
                        if 'application/json' in body_content:
                            body_schema = body_content['application/json'].get('schema', {})
                            if 'example' in body_schema:
                                body = body_schema['example']

                    # 解析模板列表的JSONPath和单个模板的字段名
                    template_name_path = template_mapping.get('template_name_path', '$.data[*].name')
                    template_content_path = template_mapping.get('template_content_path', '$.data[*].template_content')

                    # 提取字段名（最后一个点后的部分）
                    template_name_field = template_name_path.split('.')[-1].replace('[*]', '')
                    template_content_field = template_content_path.split('.')[-1].replace('[*]', '')

                    # 获取 group_name_pattern
                    group_name_pattern = template_mapping.get('group_name_pattern', '$.name + 服务记录')

                    return {
                        "api_schema": api_schema_yaml,
                        "url": full_url,
                        "method": method.upper(),
                        "headers": headers,
                        "body": body,
                        "template_list_path": template_name_path.rsplit('.', 1)[0] if '.' in template_name_path else '$',
                        "template_name_field": template_name_field,
                        "template_content_field": template_content_field,
                        "group_name_pattern": group_name_pattern,
                        "parse_prompt": template_mapping.get('parse_prompt', DEFAULT_TEMPLATE_PARSE_PROMPT),
                        "selector_field_name": template_mapping.get('selector_field_name', 'template_selector'),
                        "selector_field_label": template_mapping.get('selector_field_label', '选择模板'),
                        "label_path": template_mapping.get('label_path', '$.data[*].templateName'),
                        "value_path": template_mapping.get('value_path', '$.data[*].id')
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
