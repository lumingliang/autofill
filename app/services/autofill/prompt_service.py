"""
Prompt模板组装服务 - 支持Function Calling和纯文本双模式
"""
from typing import Any, Dict, List, Optional

from app.models.autofill import FieldGroupConfig, FieldSpec


def build_fields_instructions(fields: List[FieldSpec]) -> str:
    """
    组装字段指令（用于纯文本Prompt和Function Calling描述）

    Args:
        fields: 字段明细列表

    Returns:
        组装后的字段指令字符串
    """
    lines = []
    for field in fields:
        if field.field_type.value == 'text':
            desc = field.fill_instruction or "根据对话内容提取"
            if field.corrections:
                corrections_text = "；".join([c['text'] for c in field.corrections])
                desc += f"。人工补充规则：{corrections_text}"
            lines.append(f"- {field.field_label}（字段名：`{field.field_name}`）：{desc}")

        elif field.field_type.value == 'select':
            items = [opt for opt in (field.options or {}).get('items', []) if not opt.get('is_deleted', False)]
            option_strs = []
            for opt in items:
                label = opt['label']
                fill_inst = opt.get('fill_instruction', '')
                corrections_list = opt.get('corrections', [])
                corrections_text = "；".join([c['text'] for c in corrections_list])
                full_desc = f"{label}：{fill_inst}" if fill_inst else label
                if corrections_text:
                    full_desc += f"；人工补充：{corrections_text}"
                option_strs.append(f"  - {full_desc}")

            options_block = "可选值：\n" + "\n".join(option_strs)
            global_inst = field.fill_instruction or "根据用户意图选择"
            lines.append(f"- {field.field_label}（字段名：`{field.field_name}`）：{global_inst}\n{options_block}\n  只能从上述选项中选择一个值。")

    return "\n".join(lines)


def build_function_schema(field_group: FieldGroupConfig, fields: List[FieldSpec]) -> Dict[str, Any]:
    """
    动态生成 Function Calling Schema

    Args:
        field_group: 字段组配置
        fields: 字段明细列表

    Returns:
        OpenAI Function Calling Schema
    """
    properties = {}

    for field in fields:
        if field.field_type.value == 'text':
            desc = field.fill_instruction or ""
            if field.corrections:
                corrections_text = "；".join([c['text'] for c in field.corrections])
                desc += f"；人工补充规则：{corrections_text}"
            properties[field.field_name] = {
                "type": "string",
                "description": desc
            }

        elif field.field_type.value == 'select':
            items = [opt for opt in (field.options or {}).get('items', []) if not opt.get('is_deleted', False)]
            enum_values = [opt['label'] for opt in items]
            option_descs = []
            for opt in items:
                label = opt['label']
                fill_inst = opt.get('fill_instruction', '')
                corrections_list = opt.get('corrections', [])
                corrections_text = "；".join([c['text'] for c in corrections_list])
                full = f"{label}：{fill_inst}" if fill_inst else label
                if corrections_text:
                    full += f"；人工补充：{corrections_text}"
                option_descs.append(full)

            description = f"可选值：{'；'.join(option_descs)}"
            if field.fill_instruction:
                description = field.fill_instruction + " " + description

            properties[field.field_name] = {
                "type": "string",
                "description": description,
                "enum": enum_values
            }

    return {
        "type": "function",
        "function": {
            "name": "extract_form_data",
            "description": field_group.description or "从对话中提取表单数据",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(properties.keys())
            }
        }
    }


def assemble_prompt(field_group: FieldGroupConfig, fields: List[FieldSpec], query: str) -> str:
    """
    组装纯文本Prompt

    Args:
        field_group: 字段组配置
        fields: 字段明细列表
        query: 用户查询内容

    Returns:
        组装后的Prompt字符串
    """
    template = field_group.prompt_template_base or """你是一个智能填单助手。请根据以下对话内容，提取指定字段的信息。

需要提取的字段：
{{fields_instructions}}

对话内容：
{{query}}

请严格按照字段要求提取信息，并以JSON格式返回结果。"""

    fields_instructions = build_fields_instructions(fields)
    prompt = template.replace("{{fields_instructions}}", fields_instructions)
    prompt = prompt.replace("{{query}}", query)

    return prompt


def assemble_output_prompts(field_group: FieldGroupConfig, fields: List[FieldSpec], extracted_data: Dict[str, Any]) -> Dict[str, str]:
    """
    组装多输出模板

    Args:
        field_group: 字段组配置
        fields: 字段明细列表
        extracted_data: 提取的数据

    Returns:
        各输出模板的渲染结果
    """
    output_templates = field_group.output_templates or {}
    results = {}

    # 构建字段映射（field_name -> field_label）
    field_map = {f.field_name: f for f in fields}

    for key, config in output_templates.items():
        template = config.get('template', '')
        # 替换模板中的变量
        result = template
        for field_name, value in extracted_data.items():
            placeholder = f"{{{{{field_name}}}}}"
            result = result.replace(placeholder, str(value) if value is not None else "")
        results[key] = result

    return results


async def get_field_group_with_fields(field_group_id: int) -> tuple[Optional[FieldGroupConfig], List[FieldSpec]]:
    """
    获取字段组及其关联的字段明细

    Args:
        field_group_id: 字段组ID

    Returns:
        (字段组配置, 字段明细列表)
    """
    from app.controllers.autofill import field_group_config_controller, field_spec_controller

    field_group = await field_group_config_controller.get(id=field_group_id)
    if not field_group:
        return None, []

    fields = await field_spec_controller.get_by_field_group(field_group_id)
    return field_group, fields


async def get_field_group_by_code_with_fields(code: str) -> tuple[Optional[FieldGroupConfig], List[FieldSpec]]:
    """
    通过编码获取字段组及其关联的字段明细

    Args:
        code: 字段组唯一编码

    Returns:
        (字段组配置, 字段明细列表)
    """
    from app.controllers.autofill import field_group_config_controller, field_spec_controller

    field_group = await field_group_config_controller.get_by_code(code)
    if not field_group:
        return None, []

    fields = await field_spec_controller.get_by_field_group(field_group.id)
    return field_group, fields
