"""
Prompt模板组装服务 - 支持Function Calling和纯文本双模式
"""
import re
from typing import Any, Dict, List, Optional

from app.controllers.autofill import field_group_config_controller, field_spec_controller
from app.models.autofill import FieldGroupConfig, FieldSpec


def _parse_instruction_rules(instruction: str) -> List[str]:
    """解析填写指引，提取多条规则
    
    支持按换行、分号、数字序号等方式分割多条规则
    """
    if not instruction:
        return []
    
    # 按换行或分号分割
    rules = re.split(r'[\n;；]+', instruction)
    # 清理并过滤空规则
    rules = [r.strip() for r in rules if r.strip()]
    return rules


def _classify_rule(rule: str) -> str:
    """对规则进行分类，返回规则类型标识
    
    返回：【必填】【格式】【禁止】【示例】【默认】【其他】
    """
    rule_lower = rule.lower()
    
    # 必填/必须规则
    if any(kw in rule_lower for kw in ['必填', '必须', '不能不', '一定要', '必需']):
        return "【必填】"
    
    # 禁止/不能规则
    if any(kw in rule_lower for kw in ['禁止', '不能', '不允许', '不要', '勿', '不得', '不可']):
        return "【禁止】"
    
    # 格式规则
    if any(kw in rule_lower for kw in ['格式', '形如', '例如', '示例', '样例', 'yyyy', 'mm', 'dd', '@', '电话', '手机', '邮箱', '日期', '时间']):
        return "【格式】"
    
    # 示例规则
    if any(kw in rule_lower for kw in ['举例', '比如', '如：', '例如：', '示例：']):
        return "【示例】"
    
    # 默认值规则
    if any(kw in rule_lower for kw in ['默认', '未提供', '未提及', '无信息']):
        return "【默认】"
    
    # 其他规则
    return "【规则】"


def _indent_multiline_text(text: str, indent: str) -> str:
    """为多行文本添加缩进
    
    Args:
        text: 原始文本
        indent: 缩进字符串
        
    Returns:
        添加缩进后的文本
    """
    lines = text.split('\n')
    if len(lines) <= 1:
        return text
    
    # 第一行不缩进，后续行添加缩进
    result = [lines[0]]
    for line in lines[1:]:
        if line.strip():  # 只缩进非空行
            result.append(indent + line)
        else:
            result.append(line)
    return '\n'.join(result)


def build_fields_instructions(fields: List, is_plain: bool = False) -> str:
    """
    组装字段指令（用于纯文本Prompt和Function Calling描述）
    
    使用混合格式：# 模块 + - 层级

    Args:
        fields: 字段明细列表（支持模型对象或dict）
        is_plain: 是否为plain模式，plain模式下使用简化格式

    Returns:
        组装后的字段指令字符串
    """
    sections = []
    
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

        if is_plain:
            # Plain模式：简化格式，直接输出填写指引
            instruction = fill_instruction or "根据内容提取"
            if corrections:
                corrections_text = "；".join([c['text'] for c in corrections])
                instruction += f"（注意：{corrections_text}）"
            sections.append(f"- {instruction}")
        else:
            # 结构化模式：混合格式（# 模块 + - 层级）
            field_section = []
            
            # # 层级1：字段模块
            type_desc = {
                'text': '文本',
                'select_single': '单选',
                'select_multi': '多选'
            }.get(field_type, field_type)
            field_section.append(f"# `{field_name}`（{field_label}）- {type_desc}")
            
            # ## 层级1.1：填写规则
            rules = _parse_instruction_rules(fill_instruction)
            if rules or corrections:
                field_section.append("## 填写规则")
                
                # 主要规则
                for rule in rules:
                    rule_type = _classify_rule(rule)
                    # 处理多行规则的缩进
                    indented_rule = _indent_multiline_text(f"{rule_type}{rule}", "    ")
                    field_section.append(f"- {indented_rule}")
                
                # 补充规则
                if corrections:
                    corrections_text = "；".join([c['text'] for c in corrections])
                    field_section.append(f"- 【补充】{corrections_text}")
            
            # ## 层级1.2：选项（仅下拉类型）
            if field_type in ['select_single', 'select_multi']:
                items = [opt for opt in (options or {}).get('items', []) if not opt.get('is_deleted', False)]
                
                if items:
                    field_section.append("## 可选值")
                    
                    for opt in items:
                        label = opt['label']
                        opt_instruction = opt.get('fill_instruction', '')
                        opt_corrections = opt.get('corrections', [])
                        
                        # 选项名称作为子模块
                        field_section.append(f"### {label}")
                        
                        # 选项规则（支持多行，保留原始格式）
                        if opt_instruction:
                            # 检查是否包含分号或序号（表示多条规则）
                            has_separators = ';' in opt_instruction or '；' in opt_instruction
                            has_numbered = bool(re.search(r'^\d+[.．、]', opt_instruction, re.MULTILINE))
                            
                            if has_separators or has_numbered:
                                # 包含分隔符，按规则解析
                                opt_rules = _parse_instruction_rules(opt_instruction)
                                for rule in opt_rules:
                                    rule_type = _classify_rule(rule)
                                    field_section.append(f"- {rule_type}{rule}")
                            else:
                                # 纯多行描述，保留整体格式
                                rule_type = _classify_rule(opt_instruction)
                                indented_instruction = _indent_multiline_text(f"{rule_type}{opt_instruction}", "  ")
                                field_section.append(f"- {indented_instruction}")
                        
                        # 选项补充规则（支持多行）
                        if opt_corrections:
                            for corr in opt_corrections:
                                corr_text = corr.get('text', '')
                                if corr_text:
                                    indented_corr = _indent_multiline_text(f"【补充】{corr_text}", "  ")
                                    field_section.append(f"- {indented_corr}")
                
                # ## 层级1.3：选择限制
                field_section.append("## 选择限制")
                if field_type == 'select_multi':
                    min_selections = options.get('min_selections', 1)
                    max_selections = options.get('max_selections', 0)
                    if max_selections > 0:
                        limit_desc = f"至少选 {min_selections} 项，最多选 {max_selections} 项"
                    else:
                        limit_desc = f"至少选 {min_selections} 项"
                    field_section.append(f"- 【多选】{limit_desc}")
                    field_section.append(f"- 【返回格式】以数组形式返回选中的值")
                else:
                    field_section.append(f"- 【单选】只能从上述选项中选择一项")
            
            sections.append('\n'.join(field_section))

    return '\n\n'.join(sections)


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
