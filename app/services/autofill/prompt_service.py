"""
Prompt模板组装服务 - 支持Function Calling和纯文本双模式
"""
from typing import Any, Dict, List, Optional

from app.controllers.autofill import field_group_config_controller, field_spec_controller
from app.models.autofill import FieldGroupConfig, FieldSpec


def build_fields_instructions(fields: List) -> str:
    """
    组装字段指令（用于纯文本Prompt和Function Calling描述）

    Args:
        fields: 字段明细列表（支持模型对象或dict）

    Returns:
        组装后的字段指令字符串
    """
    lines = []
    for field in fields:
        # 兼容模型对象和 dict 两种格式
        if isinstance(field, dict):
            field_type = field.get("field_type", "")
            field_name = field.get("field_name", "")
            field_label = field.get("field_label", field_name)
            fill_instruction = field.get("fill_instruction", "")
            corrections = field.get("corrections", [])
            options = field.get("options", {})
        else:
            field_type = field.field_type.value if hasattr(field.field_type, 'value') else str(field.field_type)
            field_name = field.field_name
            field_label = field.field_label
            fill_instruction = field.fill_instruction
            corrections = field.corrections
            options = field.options

        if field_type == 'text':
            desc = fill_instruction or "根据对话内容提取"
            if corrections:
                corrections_text = "；".join([c['text'] for c in corrections])
                desc += f"。人工补充规则：{corrections_text}"
            lines.append(f"- {field_label}（字段名：`{field_name}`）：{desc}")

        elif field_type in ['select_single', 'select_multi']:
            items = [opt for opt in (options or {}).get('items', []) if not opt.get('is_deleted', False)]
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
            global_inst = fill_instruction or "根据用户意图选择"

            # 获取数量限制配置（仅多选时有效）
            min_selections = options.get('min_selections', 1)
            max_selections = options.get('max_selections', 0)

            if field_type == 'select_multi':
                # 多选模式
                count_desc = f"请选择 {min_selections} 到 {max_selections} 个选项" if max_selections > 0 else f"请至少选择 {min_selections} 个选项"
                lines.append(f"- {field_label}（字段名：`{field_name}`）：{global_inst}\n{options_block}\n  【多选】{count_desc}，以数组形式返回选中的值。")
            else:
                # 单选模式
                lines.append(f"- {field_label}（字段名：`{field_name}`）：{global_inst}\n{options_block}\n  【单选】只能从上述选项中选择一个值。")

    return "\n".join(lines)


def build_function_schema(field_group: FieldGroupConfig, fields: List[FieldSpec], include_reason: bool = False) -> Dict[str, Any]:
    """
    动态生成 Function Calling Schema
    可选择为每个字段添加对应的理由字段

    Args:
        field_group: 字段组配置
        fields: 字段明细列表
        include_reason: 是否包含理由字段

    Returns:
        OpenAI Function Calling Schema
    """
    properties = {}

    for field in fields:
        field_name = field.field_name
        field_label = field.field_label
        reason_field_name = f"{field_name}_reason"

        if field.field_type.value == 'text':
            desc = field.fill_instruction or ""
            if field.corrections:
                corrections_text = "；".join([c['text'] for c in field.corrections])
                desc += f"；人工补充规则：{corrections_text}"
            properties[field_name] = {
                "type": "string",
                "description": desc
            }
            # 添加理由字段（仅在 include_reason=True 时）
            if include_reason:
                properties[reason_field_name] = {
                    "type": "string",
                    "description": f"填写'{field_label}'字段的理由，说明从对话中哪个部分提取的信息"
                }

        elif field.field_type.value in ['select_single', 'select_multi']:
            items = [opt for opt in (field.options or {}).get('items', []) if not opt.get('is_deleted', False)]
            enum_values = [opt['label'] for opt in items]

            # 获取数量限制配置（仅多选时有效）
            options = field.options or {}
            min_selections = options.get('min_selections', 1)
            max_selections = options.get('max_selections', 0)

            # 构建格式化的选项描述，使用换行符让LLM更容易理解
            option_lines = []
            for opt in items:
                label = opt['label']
                fill_inst = opt.get('fill_instruction', '')
                corrections_list = opt.get('corrections', [])
                corrections_text = "；".join([c['text'] for c in corrections_list])

                line = f"  - {label}"
                if fill_inst:
                    line += f"：{fill_inst}"
                if corrections_text:
                    line += f"（人工补充：{corrections_text}）"
                option_lines.append(line)

            # 组合描述：字段指引 + 格式化选项列表 + 选择模式说明
            description_parts = []
            if field.fill_instruction:
                description_parts.append(field.fill_instruction)
            description_parts.append("可选值：")
            description_parts.extend(option_lines)

            if field.field_type.value == 'select_multi':
                # 多选模式
                count_desc = f"请选择 {min_selections} 到 {max_selections} 个选项" if max_selections > 0 else f"请至少选择 {min_selections} 个选项"
                description_parts.append(f"【多选】{count_desc}，以字符串数组形式返回选中的值。")

                # 多选使用数组类型
                properties[field_name] = {
                    "type": "array",
                    "description": "\n".join(description_parts),
                    "items": {
                        "type": "string",
                        "enum": enum_values
                    },
                    "minItems": min_selections,
                    "maxItems": max_selections if max_selections > 0 else None
                }
                # 移除 None 值
                if properties[field_name]["maxItems"] is None:
                    del properties[field_name]["maxItems"]
            else:
                # 单选模式
                description_parts.append("【单选】必须从上述选项中选择一个值。")
                description = "\n".join(description_parts)

                properties[field_name] = {
                    "type": "string",
                    "description": description,
                    "enum": enum_values
                }
            
            # 添加理由字段（单选和多选都添加，仅在 include_reason=True 时）
            if include_reason:
                properties[reason_field_name] = {
                    "type": "string",
                    "description": f"选择'{field_label}'字段值的理由，说明从对话中哪个部分提取的信息"
                }

    # 根据 include_reason 设置描述
    description = field_group.description or "从对话中提取表单数据"
    if include_reason:
        description += "，每个字段都需要提供填写理由"

    return {
        "type": "function",
        "function": {
            "name": "extract_form_data",
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(properties.keys())
            }
        }
    }


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
    field_group = await field_group_config_controller.get_by_code(code)
    if not field_group:
        return None, []

    fields = await field_spec_controller.get_by_field_group(field_group.id)
    return field_group, fields
