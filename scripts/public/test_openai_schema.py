#!/usr/bin/env python3
"""验证重构后的接口返回的 Schema 符合 OpenAI 规范"""

import asyncio
import httpx
import json

API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
BASE_URL = "http://localhost:9999"


def validate_openai_function_schema(schema: dict) -> tuple[bool, list]:
    """验证 Function Schema 是否符合 OpenAI 规范"""
    errors = []
    
    if schema.get("type") != "function":
        errors.append("type 必须是 'function'")
    
    func = schema.get("function", {})
    if not func:
        errors.append("缺少 function 对象")
        return False, errors
    
    name = func.get("name")
    if not name:
        errors.append("function.name 不能为空")
    elif not isinstance(name, str):
        errors.append("function.name 必须是字符串")
    elif not name.isidentifier():
        errors.append(f"function.name '{name}' 必须是有效的标识符")
    
    params = func.get("parameters", {})
    if not params:
        errors.append("function.parameters 不能为空")
    else:
        if params.get("type") != "object":
            errors.append("parameters.type 必须是 'object'")
        
        properties = params.get("properties", {})
        if not properties:
            errors.append("parameters.properties 不能为空")
        
        required = params.get("required", [])
        if not isinstance(required, list):
            errors.append("parameters.required 必须是数组")
        
        for prop_name, prop_def in properties.items():
            if not isinstance(prop_def, dict):
                errors.append(f"properties.{prop_name} 必须是对象")
                continue
            
            prop_type = prop_def.get("type")
            if not prop_type:
                errors.append(f"properties.{prop_name}.type 不能为空")
            elif prop_type not in ["string", "number", "integer", "boolean", "array", "object"]:
                errors.append(f"properties.{prop_name}.type '{prop_type}' 不是有效的类型")
            
            if "enum" in prop_def:
                enum_values = prop_def["enum"]
                if not isinstance(enum_values, list):
                    errors.append(f"properties.{prop_name}.enum 必须是数组")
                elif len(enum_values) == 0:
                    errors.append(f"properties.{prop_name}.enum 不能为空")
                else:
                    for i, val in enumerate(enum_values):
                        if not isinstance(val, str):
                            errors.append(f"properties.{prop_name}.enum[{i}] 必须是字符串")
            
            for req_field in required:
                if req_field not in properties:
                    errors.append(f"required 中的字段 '{req_field}' 不在 properties 中")
    
    return len(errors) == 0, errors


async def main():
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        print("="*60)
        print("验证重构后的接口 Schema 规范")
        print("="*60)
        
        resp = await client.post(
            f"{BASE_URL}/api/autofill/field_groups/schema",
            headers=headers,
            json={
                "page_name": "用户信息页",
                "field_names": ["一级事件类型", "智能网联-二三级"]
            }
        )
        data = resp.json().get("data", {})
        
        # 验证 Function Schema
        schema = data.get("function_calling", {}).get("schema", {})
        is_valid, errors = validate_openai_function_schema(schema)
        
        print("\n【Function Schema 验证】")
        if is_valid:
            print("✅ 符合 OpenAI Function Calling 规范")
        else:
            print("❌ 不符合规范，错误列表:")
            for err in errors:
                print(f"  - {err}")
        
        # 验证 Prompt 完整性
        print("\n【Prompt 信息验证】")
        prompt_info = data.get("prompt_info", {})
        checks = [
            ("template_base 存在", bool(prompt_info.get("template_base"))),
            ("fields_instructions 存在", bool(prompt_info.get("fields_instructions"))),
            ("assembled_prompt 存在", bool(prompt_info.get("assembled_prompt"))),
            ("template_base 包含 {{fields_instructions}}", "{{fields_instructions}}" in prompt_info.get("template_base", "")),
            ("template_base 包含 {{query}}", "{{query}}" in prompt_info.get("template_base", "")),
            ("assembled_prompt 已替换占位符", "{{" not in prompt_info.get("assembled_prompt", "")),
        ]
        
        for name, result in checks:
            print(f"{'✅' if result else '❌'} {name}")
        
        # 验证字段列表
        print("\n【字段列表验证】")
        fields = data.get("fields", [])
        print(f"字段数量: {len(fields)}")
        if fields:
            print(f"字段名: {[f.get('field_name') for f in fields]}")
            
            # 检查字段结构
            first_field = fields[0]
            field_checks = [
                ("id 存在", "id" in first_field),
                ("field_name 存在", "field_name" in first_field),
                ("field_label 存在", "field_label" in first_field),
                ("field_type 存在", "field_type" in first_field),
                ("fill_instruction 存在", "fill_instruction" in first_field),
                ("options 存在", "options" in first_field),
            ]
            for name, result in field_checks:
                print(f"{'✅' if result else '❌'} {name}")
        
        # 验证 merged_config
        print("\n【Merged Config 验证】")
        merged_config = data.get("merged_config", {})
        config_checks = [
            ("prompt_template_base 存在", "prompt_template_base" in merged_config),
            ("output_templates 存在", "output_templates" in merged_config),
            ("description 存在", "description" in merged_config),
        ]
        for name, result in config_checks:
            print(f"{'✅' if result else '❌'} {name}")
        
        print("\n" + "="*60)
        print("验证完成!")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
