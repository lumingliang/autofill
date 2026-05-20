"""
模板类型字段服务
处理模板类型字段的同步和解析
"""
import json
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
    FieldType,
    FillPage
)
from app.utils.curl_parser import parse_curl_command


DEFAULT_TEMPLATE_PARSE_PROMPT = """你是一个专业的模板解析助手。请分析以下模板内容，提取关键信息字段。

## 输入模板内容
{template_content}

## 解析要求
1. 分析模板内容，识别所有需要填写的关键信息点
2. 为每个关键信息提取字段：
   - field_name: 字段英文名（小写，下划线连接，如：customer_name）
   - field_label: 字段中文标签（清晰易懂的中文名称）
   - field_type: 字段类型（默认为 "text"）
   - fill_instruction: 填写指引（必须包含以下所有约束信息，从模板中提取）
3. 字段类型说明：
   - 所有字段默认使用 "text" 类型
   - 只有在模板中明确说明是选择类型（如是/否、多选等）时才使用 "select_single" 或 "select_multi"

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

## 输出格式（JSON）
你必须严格按照以下JSON格式返回，不要添加任何其他内容：

{
    "standard_template": "车主姓名: ${customer_name}\\n联系电话: ${contact_phone}\\n服务类型: ${service_type}",
    "fields": [
        {"field_name": "customer_name", "field_label": "车主姓名", "field_type": "text", "fill_instruction": "客户姓名，字符串类型，如：张先生、李女士。必填。"},
        {"field_name": "contact_phone", "field_label": "联系电话", "field_type": "text", "fill_instruction": "客户联系电话，11位手机号码，数字格式。必填。"},
        {"field_name": "service_type", "field_label": "服务类型", "field_type": "text", "fill_instruction": "服务类型，如：道路救援、保养预约、维修服务。必填。"}
    ]
}

## 重要说明
1. standard_template 必须是一个字符串，格式为：字段标签: ${field_name}，每个字段占一行，用 \\n 分隔
2. 示例格式："车主姓名: ${customer_name}\\n联系电话: ${contact_phone}\\n地址: ${address}"
3. 根据实际提取的字段生成对应的 standard_template，不要照搬示例
4. 字段名使用英文小写，下划线连接
5. 字段标签使用中文，清晰易懂
6. **fill_instruction 必须全面**：整合字段含义、格式、类型、范围、标准、必填要求等所有约束信息
7. 所有字段默认类型为 "text"，不要猜测字段类型
8. 只返回JSON，不要包含任何解释说明
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

            # 4. 遍历处理每个模板
            results = []
            for template in templates:
                try:
                    result = await self._process_single_template(
                        template,
                        template_config,
                        field_spec
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"[TemplateFieldService] 处理模板失败: {e}")
                    results.append({
                        "success": False,
                        "error": str(e)
                    })

            # 5. 更新状态为completed
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
        template_content = template.get(template_content_field)

        if not template_name:
            logger.error(f"[TemplateFieldService] 无法提取模板名称，字段: {template_name_field}, 可用字段: {list(template.keys())}")
            raise ValueError(f"无法提取模板名称，字段 '{template_name_field}' 不存在")
        if not template_content:
            logger.error(f"[TemplateFieldService] 无法提取模板内容，字段: {template_content_field}, 可用字段: {list(template.keys())}")
            raise ValueError(f"无法提取模板内容，字段 '{template_content_field}' 不存在")

        logger.info(f"[TemplateFieldService] 处理模板: {template_name}")

        # 4.2 使用LLM解析
        # 直接将原始模板内容传给大模型，让大模型自己解析
        # 不再使用 parse_prompt.format() 方式
        # 优先使用字段的自定义提示词，其次使用模板配置中的提示词，最后使用默认提示词
        parse_prompt = field_spec.options.get("parse_prompt") or template_config.get("parse_prompt") or DEFAULT_TEMPLATE_PARSE_PROMPT

        parsed = await self._parse_template_with_llm(template_content, parse_prompt)

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

        # 转换字段格式，提取 fill_instruction
        fields_for_group = []
        for field in parsed["fields"]:
            field_data = {
                "field_name": field["field_name"],
                "field_label": field["field_label"],
                "field_type": field["field_type"],
                "fill_instruction": field.get("fill_instruction", f"请填写{field['field_label']}"),
                "options": field.get("options", {})
            }
            fields_for_group.append(field_data)

        await field_group_service.upsert_field_group(
            tenant_id=field_spec.tenant_id,
            app_name=field_spec.app_name,
            page_name=page.page_name,
            group_name=group_name,
            output_templates={"default": {"template": parsed["standard_template"]}},
            fields=fields_for_group
        )

        return {
            "success": True,
            "template_name": template_name,
            "group_name": group_name,
            "fields_count": len(parsed.get("fields", []))
        }

    async def _fetch_templates(
        self,
        template_config: Dict
    ) -> List[Dict]:
        """
        根据curl配置获取外部模板列表
        """
        curl_command = template_config.get("curl_command", "")
        if not curl_command:
            raise ValueError("缺少curl_command配置")

        # 解析curl命令
        curl_config = parse_curl_command(curl_command)

        method = curl_config.get("method", "GET")
        url = curl_config.get("url", "")
        headers = curl_config.get("headers", {})
        body = curl_config.get("body")

        if not url:
            raise ValueError("无法从curl命令中提取URL")

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

        # 使用template_list_path提取模板列表
        template_list_path = template_config.get("template_list_path", "$.data[*]")
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

    async def _parse_template_with_llm(
        self,
        template_content: str,
        parse_prompt: str
    ) -> Dict[str, Any]:
        """
        使用LLM解析模板内容

        返回: {
            "standard_template": "标准化后的模板",
            "fields": [
                {"field_name": "contact_phone", "field_label": "联系电话", "field_type": "text"},
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
        # 不再使用 format() 方式，避免模板内容中的特殊字符被误解析
        full_prompt = f"{parse_prompt}\n\n## 输入模板内容\n{template_content}"

        logger.info(f"[TemplateFieldService] 调用LLM解析模板，模型: {config.name}")

        # 3. 调用LLM服务
        result = await llm_proxy_service.process_request(
            query=full_prompt,
            tools=[],  # plain模式不需要tools
            system_prompt="你是一个专业的模板解析助手，擅长从非标准模板中提取结构化信息。",
            method="plain",  # 使用plain模式直接返回文本
            config=config
        )

        if not result.get("success"):
            error_msg = result.get("error", "未知错误")
            logger.error(f"[TemplateFieldService] LLM调用失败: {error_msg}")
            raise ValueError(f"LLM解析失败: {error_msg}")

        # 4. 解析JSON响应
        try:
            content = result.get("data", "")

            # 处理LLM返回的数据结构
            # 情况1: content是字符串，直接解析JSON
            # 情况2: content是字典，包含raw_response和content键（LLM代理返回的结构）
            if isinstance(content, dict):
                # 检查是否是LLM代理返回的结构
                if "content" in content:
                    # 真正的内容在content键中
                    content = content["content"]
                elif "raw_response" in content:
                    # 尝试从raw_response获取
                    content = content["raw_response"]

            if isinstance(content, dict):
                # 如果content已经是字典，直接使用
                parsed = content
            else:
                # 清理可能的markdown代码块
                content_str = str(content).strip()
                if content_str.startswith("```json"):
                    content_str = content_str[7:]
                if content_str.startswith("```"):
                    content_str = content_str[3:]
                if content_str.endswith("```"):
                    content_str = content_str[:-3]
                content_str = content_str.strip()

                # 处理LLM返回的转义JSON字符串
                # 情况1: 内容被包裹在单引号中，如: '{"key": "value"}'
                # 情况2: 内容使用双花括号，如: '{{"key": "value"}}'
                # 情况3: 内容包含转义字符，如: '{\\n  "key": "value"\\n}'

                # 首先尝试直接解析
                try:
                    parsed = json.loads(content_str)
                except json.JSONDecodeError:
                    # 处理各种转义情况
                    processed_str = content_str

                    # 去除外层单引号（如果存在）
                    if (processed_str.startswith("'") and processed_str.endswith("'")) or \
                       (processed_str.startswith('"') and processed_str.endswith('"')):
                        processed_str = processed_str[1:-1]

                    # 处理双花括号（Jinja2风格转义）
                    if processed_str.startswith("{{") and processed_str.endswith("}}"):
                        processed_str = processed_str[1:-1].strip()

                    # 处理Python字符串转义
                    # 将 \\n 转换为实际的换行符，\\" 转换为 "
                    try:
                        processed_str = processed_str.encode('utf-8').decode('unicode_escape')
                    except UnicodeDecodeError:
                        pass  # 如果解码失败，保持原样

                    try:
                        parsed = json.loads(processed_str)
                    except json.JSONDecodeError as e2:
                        logger.error(f"[TemplateFieldService] JSON解析失败，原始内容: {content_str[:200]}...")
                        logger.error(f"[TemplateFieldService] 处理后内容: {processed_str[:200]}...")
                        raise e2

            # 5. 验证返回格式
            if "standard_template" not in parsed or "fields" not in parsed:
                logger.error(f"[TemplateFieldService] LLM返回格式不正确: {parsed}")
                logger.error(f"[TemplateFieldService] parsed类型: {type(parsed)}, keys: {parsed.keys() if isinstance(parsed, dict) else 'N/A'}")
                raise ValueError("LLM返回格式不正确，缺少standard_template或fields")

            # 6. 验证字段格式并转换
            fields = []
            for field in parsed.get("fields", []):
                # 支持 name/label/type/fill_instruction 和 field_name/field_label/field_type/fill_instruction 两种格式
                field_name = field.get("field_name") or field.get("name")
                field_label = field.get("field_label") or field.get("label")
                field_type = field.get("field_type") or field.get("type")
                fill_instruction = field.get("fill_instruction") or field.get("field_guide") or field.get("guide") or field.get("description")

                if not field_name or not field_label:
                    logger.warning(f"[TemplateFieldService] 字段缺少名称或标签: {field}")
                    continue

                # 构建字段数据，确保有填写指引
                field_data = {
                    "field_name": field_name,
                    "field_label": field_label,
                    "field_type": field_type or "text",
                    "fill_instruction": fill_instruction or f"请填写{field_label}"
                }
                fields.append(field_data)

            logger.info(f"[TemplateFieldService] LLM解析成功，提取 {len(fields)} 个字段")

            # 检查并修复 standard_template 格式
            standard_template = parsed.get("standard_template", "")
            # 将 \\n 替换为实际的换行符
            standard_template = standard_template.replace("\\n", "\n")
            
            # 检查格式是否正确：每行应该是 "字段标签: ${field_name}" 格式
            # 正确的格式：每行包含冒号分隔的标签和变量引用
            lines = standard_template.split('\n')
            is_correct_format = True
            
            # 检查是否包含默认模板标记
            if "${field_name}" in standard_template or "${value}" in standard_template:
                is_correct_format = False
                logger.warning(f"[TemplateFieldService] standard_template包含默认模板标记")
            else:
                # 检查每行格式是否符合 "标签: ${变量名}"
                field_pattern = re.compile(r'^[^:]+:\s*\$\{[^}]+\}$')
                valid_lines = 0
                for line in lines:
                    line = line.strip()
                    if line and field_pattern.match(line):
                        valid_lines += 1
                
                # 如果有效行数少于字段数的一半，认为格式不正确
                if valid_lines < len(fields) / 2:
                    is_correct_format = False
                    logger.warning(f"[TemplateFieldService] standard_template格式检查失败: 有效行{valid_lines}, 字段数{len(fields)}")
            
            if not is_correct_format:
                # LLM没有返回正确的格式，使用字段列表自动生成
                logger.warning(f"[TemplateFieldService] LLM返回的standard_template格式不正确，自动生成正确格式")
                template_lines = []
                for field in fields:
                    field_label = field.get("field_label", field.get("field_name", ""))
                    field_name = field.get("field_name", "")
                    template_lines.append(f"{field_label}: ${{{field_name}}}")
                standard_template = "\n".join(template_lines)
                logger.info(f"[TemplateFieldService] 自动生成的standard_template:\n{standard_template}")
            else:
                logger.info(f"[TemplateFieldService] LLM返回的standard_template格式正确，共{len(lines)}行")

            return {
                "standard_template": standard_template,
                "fields": fields
            }

        except json.JSONDecodeError as e:
            logger.error(f"[TemplateFieldService] LLM返回内容不是有效的JSON: {e}, 内容: {result.get('data')}")
            raise ValueError(f"LLM返回内容不是有效的JSON: {e}")
        except Exception as e:
            logger.error(f"[TemplateFieldService] 解析LLM响应失败: {e}")
            raise ValueError(f"解析LLM响应失败: {e}")

    async def _generate_group_name(
        self,
        pattern: str,
        template_data: Dict,
        parent_template: Dict = None
    ) -> str:
        """
        根据规则生成字段组名称

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

            # 使用jsonpath提取值
            jsonpath_expr = jsonpath_parse(jsonpath_part)
            matches = jsonpath_expr.find(data_to_search)

            if matches:
                template_name = matches[0].value
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

    def _extract_by_jsonpath(
        self,
        data: Dict,
        jsonpath: str
    ) -> Any:
        """使用JSONPath从数据中提取值

        如果JSONPath包含 [*] 通配符，返回所有匹配项的列表
        否则返回第一个匹配项的值
        """
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
            "curl_command": "...",
            "template_name_path": "...",
            "template_content_path": "...",
            "group_name_pattern": "...",
            "parse_prompt": "..."
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

                    # 获取 x-api-params 配置
                    api_params = operation.get('x-api-params', {})

                    # 构建curl命令
                    servers = schema.get('servers', [{}])
                    base_url = servers[0].get('url', '') if servers else ''

                    # 如果没有配置servers，使用默认的localhost地址
                    if not base_url:
                        base_url = 'http://localhost:3200'

                    # 确保base_url和path正确拼接
                    if base_url.endswith('/') and path.startswith('/'):
                        full_url = f"{base_url[:-1]}{path}"
                    elif not base_url.endswith('/') and not path.startswith('/'):
                        full_url = f"{base_url}/{path}"
                    else:
                        full_url = f"{base_url}{path}"

                    # 构建curl命令
                    curl_parts = [f"curl -X {method.upper()} '{full_url}'"]

                    # 添加headers
                    headers = api_params.get('headers', {})
                    for key, value in headers.items():
                        curl_parts.append(f"  -H '{key}: {value}'")

                    # 添加body（如果有）
                    if 'requestBody' in operation:
                        body_content = operation['requestBody'].get('content', {})
                        if 'application/json' in body_content:
                            body_schema = body_content['application/json'].get('schema', {})
                            if 'example' in body_schema:
                                body_json = json.dumps(body_schema['example'], ensure_ascii=False)
                                curl_parts.append(f"  -H 'Content-Type: application/json'")
                                curl_parts.append(f"  -d '{body_json}'")

                    curl_command = ' \\\n'.join(curl_parts)

                    # 解析模板列表的JSONPath和单个模板的字段名
                    # 例如: $.data[*].name -> 列表路径: $.data[*], 字段名: name
                    template_name_path = template_mapping.get('template_name_path', '$.data[*].name')
                    template_content_path = template_mapping.get('template_content_path', '$.data[*].template_content')

                    # 提取字段名（最后一个点后的部分）
                    template_name_field = template_name_path.split('.')[-1].replace('[*]', '')
                    template_content_field = template_content_path.split('.')[-1].replace('[*]', '')

                    # 获取 group_name_pattern，使用 JSONPath 格式
                    group_name_pattern = template_mapping.get('group_name_pattern', '$.name + 服务记录')
                    # 兼容旧格式：如果包含 {template_name}，转换为 JSONPath 格式
                    if '{template_name}' in group_name_pattern:
                        group_name_pattern = '$.name + 服务记录'

                    return {
                        "curl_command": curl_command,
                        "template_list_path": template_name_path.rsplit('.', 1)[0] if '.' in template_name_path else '$',
                        "template_name_field": template_name_field,
                        "template_content_field": template_content_field,
                        "group_name_pattern": group_name_pattern,
                        "parse_prompt": template_mapping.get('parse_prompt', DEFAULT_TEMPLATE_PARSE_PROMPT)
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
