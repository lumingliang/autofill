"""
FC Schema 统一构建工具类
根据 fc.md 的企业级标准方案实现

核心架构：
1. DB 字段 → 构建标准 FC tools 参数（唯一数据源）
2. FC tools 参数 → 反向生成 Pydantic 动态模型
3. FC tools 参数 → 反向生成 Json 动态提示词

统一源头：FC Schema
一次构建，三端复用
"""
import json
from typing import Any, Dict, List, Literal, Optional, Type

from pydantic import BaseModel, Field, create_model


class FCSchemaBuilder:
    """
    统一构建器：
    DB → FC → Pydantic → JsonPrompt
    """

    @staticmethod
    def build_fc_tools(
        db_fields: List[Dict[str, Any]],
        function_name: str = "fill_form",
        include_reason: bool = False,
        description: str = "自动填充表单"
    ) -> List[Dict[str, Any]]:
        """
        【源头】DB 字段 → 标准 FC tools (OpenAI 格式)

        字段说明：
        - field_name: str     # JSON 输出字段名
        - field_label: str    # 显示名
        - field_type: str     # text / single_select / multi_select / select_single / select_multi
        - fill_instruction: str # 填写指引
        - options: dict       # { items, min_selections, max_selections }
        - corrections: list   # 人工补充规则
        """
        properties = {}
        required = []

        for f in db_fields:
            fname = f["field_name"]
            f_type = f["field_type"]
            label = f["field_label"]
            instruction = f.get("fill_instruction", "")
            options = f.get("options", {}) or {}
            corrections = f.get("corrections", [])
            reason_field_name = f"{fname}_reason"

            # 构建描述
            desc_parts = [f"{label}"]
            if instruction:
                desc_parts.append(instruction)
            if corrections:
                corrections_text = "；".join([c["text"] if isinstance(c, dict) else str(c) for c in corrections])
                desc_parts.append(f"人工补充规则：{corrections_text}")
            desc = "，".join(desc_parts)

            # 处理不同类型的字段
            if f_type in ["text"]:
                prop = {
                    "type": "string",
                    "description": desc
                }
                # 添加理由字段（仅在 include_reason=True 时）
                if include_reason:
                    properties[reason_field_name] = {
                        "type": "string",
                        "description": f"填写'{label}'字段的理由，说明从对话中哪个部分提取的信息"
                    }
                    required.append(reason_field_name)

            elif f_type in ["single_select", "select_single"]:
                items = options.get("items", [])
                # 过滤已删除的选项
                valid_items = [opt for opt in items if not opt.get("is_deleted", False)] if isinstance(items, list) else []
                enum_values = [opt["label"] if isinstance(opt, dict) else str(opt) for opt in valid_items]

                # 构建格式化的选项描述
                option_lines = []
                for opt in valid_items:
                    if isinstance(opt, dict):
                        opt_label = opt.get("label", "")
                        opt_fill_inst = opt.get("fill_instruction", "")
                        opt_corrections = opt.get("corrections", [])
                        opt_corrections_text = "；".join([c["text"] if isinstance(c, dict) else str(c) for c in opt_corrections])

                        line = f"  - {opt_label}"
                        if opt_fill_inst:
                            line += f"：{opt_fill_inst}"
                        if opt_corrections_text:
                            line += f"（人工补充：{opt_corrections_text}）"
                        option_lines.append(line)

                # 组合描述
                description_parts = []
                if instruction:
                    description_parts.append(instruction)
                description_parts.append("可选值：")
                description_parts.extend(option_lines)
                description_parts.append("【单选】必须从上述选项中选择一个值。")
                full_desc = "\n".join(description_parts)

                prop = {
                    "type": "string",
                    "description": full_desc,
                    "enum": enum_values
                }
                # 添加理由字段（仅在 include_reason=True 时）
                if include_reason:
                    properties[reason_field_name] = {
                        "type": "string",
                        "description": f"选择'{label}'字段值的理由，说明从对话中哪个部分提取的信息"
                    }
                    required.append(reason_field_name)

            elif f_type in ["multi_select", "select_multi"]:
                items = options.get("items", [])
                # 过滤已删除的选项
                valid_items = [opt for opt in items if not opt.get("is_deleted", False)] if isinstance(items, list) else []
                enum_values = [opt["label"] if isinstance(opt, dict) else str(opt) for opt in valid_items]
                min_selections = options.get("min_selections", 1)
                max_selections = options.get("max_selections", 0)

                # 构建格式化的选项描述
                option_lines = []
                for opt in valid_items:
                    if isinstance(opt, dict):
                        opt_label = opt.get("label", "")
                        opt_fill_inst = opt.get("fill_instruction", "")
                        opt_corrections = opt.get("corrections", [])
                        opt_corrections_text = "；".join([c["text"] if isinstance(c, dict) else str(c) for c in opt_corrections])

                        line = f"  - {opt_label}"
                        if opt_fill_inst:
                            line += f"：{opt_fill_inst}"
                        if opt_corrections_text:
                            line += f"（人工补充：{opt_corrections_text}）"
                        option_lines.append(line)

                # 组合描述
                count_desc = f"请选择 {min_selections} 到 {max_selections} 个选项" if max_selections > 0 else f"请至少选择 {min_selections} 个选项"
                description_parts = []
                if instruction:
                    description_parts.append(instruction)
                description_parts.append("可选值：")
                description_parts.extend(option_lines)
                description_parts.append(f"【多选】{count_desc}，以字符串数组形式返回选中的值。")
                full_desc = "\n".join(description_parts)

                prop = {
                    "type": "array",
                    "description": full_desc,
                    "items": {
                        "type": "string",
                        "enum": enum_values
                    },
                    "minItems": min_selections
                }
                if max_selections > 0:
                    prop["maxItems"] = max_selections

                # 添加理由字段（仅在 include_reason=True 时）
                if include_reason:
                    properties[reason_field_name] = {
                        "type": "string",
                        "description": f"选择'{label}'字段值的理由，说明从对话中哪个部分提取的信息"
                    }
                    required.append(reason_field_name)

            else:
                # 默认按文本处理
                prop = {
                    "type": "string",
                    "description": desc
                }

            properties[fname] = prop
            required.append(fname)

        # 根据 include_reason 设置描述
        final_description = description
        if include_reason:
            final_description += "，每个字段都需要提供填写理由"

        return {
            "type": "function",
            "function": {
                "name": function_name,
                "description": final_description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

    @staticmethod
    def build_pydantic_model_from_fc(fc_schema: Dict[str, Any]) -> Type[BaseModel]:
        """
        FC Schema → 动态 Pydantic 模型
        """
        if not fc_schema:
            raise ValueError("fc_schema 不能为空")

        func = fc_schema.get("function", {})
        params = func.get("parameters", {})
        properties = params.get("properties", {})
        required = params.get("required", [])

        fields = {}

        for name, prop in properties.items():
            desc = prop.get("description", "")
            type_ = prop.get("type")
            is_required = name in required

            if type_ == "string":
                if "enum" in prop:
                    # 单选 enum 类型
                    literal = Literal[tuple(prop["enum"])]
                    if is_required:
                        fields[name] = (literal, Field(..., description=desc))
                    else:
                        fields[name] = (Optional[literal], Field(default=None, description=desc))
                else:
                    # 文本
                    if is_required:
                        fields[name] = (str, Field(..., description=desc))
                    else:
                        fields[name] = (Optional[str], Field(default=None, description=desc))

            elif type_ == "array":
                # 多选
                items = prop.get("items", {})
                enum_vals = items.get("enum", [])
                if enum_vals:
                    literal = Literal[tuple(enum_vals)]
                    list_type = List[literal]
                else:
                    list_type = List[str]

                if is_required:
                    fields[name] = (list_type, Field(..., description=desc))
                else:
                    fields[name] = (Optional[list_type], Field(default=None, description=desc))

            elif type_ == "integer":
                if is_required:
                    fields[name] = (int, Field(..., description=desc))
                else:
                    fields[name] = (Optional[int], Field(default=None, description=desc))

            elif type_ == "number":
                if is_required:
                    fields[name] = (float, Field(..., description=desc))
                else:
                    fields[name] = (Optional[float], Field(default=None, description=desc))

            elif type_ == "boolean":
                if is_required:
                    fields[name] = (bool, Field(..., description=desc))
                else:
                    fields[name] = (Optional[bool], Field(default=None, description=desc))

            else:
                # 默认字符串
                if is_required:
                    fields[name] = (str, Field(..., description=desc))
                else:
                    fields[name] = (Optional[str], Field(default=None, description=desc))

        return create_model("DynamicFormModel", **fields)

    @staticmethod
    def build_json_prompt_from_fc(fc_schema: Dict[str, Any]) -> str:
        """
        FC Schema → 动态 JSON 提示词
        """
        if not fc_schema:
            raise ValueError("fc_schema 不能为空")

        func = fc_schema.get("function", {})
        params = func.get("parameters", {})
        properties = params.get("properties", {})

        schema = {}
        lines = []

        for name, prop in properties.items():
            desc = prop.get("description", "")
            type_ = prop.get("type")

            if type_ == "string":
                if "enum" in prop:
                    schema[name] = "单选"
                    lines.append(f"- {name}：{desc}，可选值：{prop['enum']}")
                else:
                    schema[name] = "文本"
                    lines.append(f"- {name}：{desc}")

            elif type_ == "array":
                items = prop.get("items", {})
                enum_vals = items.get("enum", [])
                min_items = prop.get("minItems", 0)
                max_items = prop.get("maxItems", 0)

                count_desc = ""
                if min_items > 0 and max_items > 0:
                    count_desc = f"，请选择 {min_items} 到 {max_items} 个选项"
                elif min_items > 0:
                    count_desc = f"，请至少选择 {min_items} 个选项"

                if enum_vals:
                    schema[name] = ["多选"]
                    lines.append(f"- {name}：{desc}，可选值：{enum_vals}{count_desc}")
                else:
                    schema[name] = ["数组"]
                    lines.append(f"- {name}：{desc}{count_desc}")

            else:
                schema[name] = type_
                lines.append(f"- {name}：{desc}")

        schema_str = json.dumps(schema, ensure_ascii=False, indent=2)
        desc_str = "\n".join(lines)

        return f"""请严格按照以下JSON格式输出，只返回JSON，不要任何多余内容：
{schema_str}

字段说明：
{desc_str}
"""

    @staticmethod
    def build_tools_description(fc_schema: Dict[str, Any]) -> str:
        """
        FC Schema → 工具描述文本
        """
        if not fc_schema:
            return ""

        func = fc_schema.get("function", {})
        name = func.get("name", "unknown")
        desc = func.get("description", "")
        params = func.get("parameters", {})

        lines = [f"工具名称：{name}", f"工具描述：{desc}", "参数："]

        if "properties" in params:
            for prop_name, prop_info in params["properties"].items():
                prop_desc = prop_info.get("description", "")
                prop_type = prop_info.get("type", "string")
                if "enum" in prop_info:
                    lines.append(f"  - {prop_name}（{prop_type}，单选）：{prop_desc}，可选值：{prop_info['enum']}")
                elif prop_type == "array":
                    items = prop_info.get("items", {})
                    enum_vals = items.get("enum", [])
                    if enum_vals:
                        lines.append(f"  - {prop_name}（数组，多选）：{prop_desc}，可选值：{enum_vals}")
                    else:
                        lines.append(f"  - {prop_name}（数组）：{prop_desc}")
                else:
                    lines.append(f"  - {prop_name}（{prop_type}）：{prop_desc}")

        return "\n".join(lines)
