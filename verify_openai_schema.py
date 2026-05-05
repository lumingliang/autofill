#!/usr/bin/env python3
"""
验证 Function Calling Schema 是否符合 OpenAI 规范
https://platform.openai.com/docs/guides/function-calling
"""

import asyncio
import httpx
import json

API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
BASE_URL = "http://localhost:9999"


def validate_openai_function_schema(schema: dict) -> tuple[bool, list]:
    """
    验证 Function Schema 是否符合 OpenAI 规范
    返回: (是否通过, 错误列表)
    """
    errors = []
    
    # 检查顶层结构
    if schema.get("type") != "function":
        errors.append("type 必须是 'function'")
    
    func = schema.get("function", {})
    if not func:
        errors.append("缺少 function 对象")
        return False, errors
    
    # 检查 function.name
    name = func.get("name")
    if not name:
        errors.append("function.name 不能为空")
    elif not isinstance(name, str):
        errors.append("function.name 必须是字符串")
    elif not name.isidentifier():
        errors.append(f"function.name '{name}' 必须是有效的标识符（只能包含字母、数字、下划线，且不能以数字开头）")
    
    # 检查 function.description
    description = func.get("description")
    if not description:
        errors.append("function.description 建议提供（虽然不是必须的，但有助于模型理解）")
    
    # 检查 parameters
    params = func.get("parameters", {})
    if not params:
        errors.append("function.parameters 不能为空对象")
    else:
        if params.get("type") != "object":
            errors.append("parameters.type 必须是 'object'")
        
        properties = params.get("properties", {})
        if not properties:
            errors.append("parameters.properties 不能为空")
        
        required = params.get("required", [])
        if not isinstance(required, list):
            errors.append("parameters.required 必须是数组")
        
        # 检查每个属性
        for prop_name, prop_def in properties.items():
            if not isinstance(prop_def, dict):
                errors.append(f"properties.{prop_name} 必须是对象")
                continue
            
            prop_type = prop_def.get("type")
            if not prop_type:
                errors.append(f"properties.{prop_name}.type 不能为空")
            elif prop_type not in ["string", "number", "integer", "boolean", "array", "object"]:
                errors.append(f"properties.{prop_name}.type '{prop_type}' 不是有效的 JSON Schema 类型")
            
            # 检查 description
            if not prop_def.get("description"):
                errors.append(f"properties.{prop_name}.description 建议提供")
            
            # 检查 enum（如果是 select 类型）
            if "enum" in prop_def:
                enum_values = prop_def["enum"]
                if not isinstance(enum_values, list):
                    errors.append(f"properties.{prop_name}.enum 必须是数组")
                elif len(enum_values) == 0:
                    errors.append(f"properties.{prop_name}.enum 不能为空数组")
                else:
                    # 检查 enum 值是否都是字符串
                    for i, val in enumerate(enum_values):
                        if not isinstance(val, str):
                            errors.append(f"properties.{prop_name}.enum[{i}] 必须是字符串，当前是 {type(val).__name__}")
            
            # 检查 required 中的字段是否都在 properties 中
            for req_field in required:
                if req_field not in properties:
                    errors.append(f"required 中的字段 '{req_field}' 不在 properties 中")
    
    return len(errors) == 0, errors


async def verify_openai_compliance():
    """验证接口返回的 Schema 是否符合 OpenAI 规范"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        print("=" * 80)
        print("验证 Function Schema 是否符合 OpenAI Function Calling 规范")
        print("=" * 80)
        
        # 测试 1: 单字段组接口
        print("\n【测试 1】/autofill/field_group 接口")
        resp = await client.post(
            f"{BASE_URL}/api/autofill/field_group",
            headers=headers,
            json={
                "page_name": "用户信息页",
                "group_names": ["default"],
                "field_names": ["一级事件类型"]
            }
        )
        data = resp.json()
        
        if data.get("code") == 200 and data.get("data"):
            fg = data["data"][0]
            schema = fg.get("function_calling", {}).get("schema", {})
            
            print(f"\nSchema 结构:")
            print(json.dumps(schema, indent=2, ensure_ascii=False))
            
            passed, errors = validate_openai_function_schema(schema)
            
            print(f"\n验证结果:")
            if passed:
                print("✅ 符合 OpenAI Function Calling 规范")
            else:
                print("❌ 不符合规范，错误列表:")
                for err in errors:
                    print(f"  - {err}")
        
        # 测试 2: 合并接口
        print("\n" + "=" * 80)
        print("【测试 2】/autofill/field_groups/schema 合并接口")
        resp = await client.post(
            f"{BASE_URL}/api/autofill/field_groups/schema",
            headers=headers,
            json={
                "page_name": "用户信息页",
                "group_names": ["default"],
                "field_names": ["一级事件类型", "智能网联-二三级"]
            }
        )
        data = resp.json()
        
        if data.get("code") == 200 and data.get("data"):
            combined = data["data"].get("combined_schema", {})
            schema = combined.get("function_calling", {}).get("schema", {})
            
            print(f"\nCombined Schema 结构:")
            print(json.dumps(schema, indent=2, ensure_ascii=False))
            
            passed, errors = validate_openai_function_schema(schema)
            
            print(f"\n验证结果:")
            if passed:
                print("✅ 符合 OpenAI Function Calling 规范")
            else:
                print("❌ 不符合规范，错误列表:")
                for err in errors:
                    print(f"  - {err}")
            
            # 额外验证：检查合并后的 schema 是否可以被正确序列化和反序列化
            print("\n【序列化验证】")
            json_str = combined.get("function_calling", {}).get("json_schema", "")
            try:
                parsed = json.loads(json_str)
                re_serialized = json.dumps(parsed, ensure_ascii=False)
                re_parsed = json.loads(re_serialized)
                
                if parsed == re_parsed:
                    print("✅ JSON 序列化/反序列化一致性检查通过")
                else:
                    print("❌ JSON 序列化/反序列化不一致")
            except Exception as e:
                print(f"❌ JSON 处理错误: {e}")


async def verify_prompt_completeness():
    """验证 Prompt 的完整性"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        print("\n" + "=" * 80)
        print("验证 Prompt 完整性")
        print("=" * 80)
        
        resp = await client.post(
            f"{BASE_URL}/api/autofill/field_groups/schema",
            headers=headers,
            json={
                "page_name": "用户信息页",
                "group_names": ["default"],
                "field_names": ["一级事件类型"]
            }
        )
        data = resp.json()
        
        if data.get("code") == 200 and data.get("data"):
            combined = data["data"].get("combined_schema", {})
            prompt_info = combined.get("prompt_info", {})
            
            print("\n【Template Base 检查】")
            template_base = prompt_info.get("template_base", "")
            if "{{fields_instructions}}" in template_base:
                print("✅ template_base 包含 {{fields_instructions}} 占位符")
            else:
                print("❌ template_base 缺少 {{fields_instructions}} 占位符")
            
            if "{{query}}" in template_base:
                print("✅ template_base 包含 {{query}} 占位符")
            else:
                print("❌ template_base 缺少 {{query}} 占位符")
            
            print("\n【Fields Instructions 检查】")
            fields_instructions = prompt_info.get("fields_instructions", "")
            if "一级事件类型" in fields_instructions:
                print("✅ fields_instructions 包含字段信息")
            else:
                print("❌ fields_instructions 缺少字段信息")
            
            if "可选值" in fields_instructions:
                print("✅ fields_instructions 包含选项信息")
            else:
                print("❌ fields_instructions 缺少选项信息")
            
            print("\n【Assembled Prompt 检查】")
            assembled = prompt_info.get("assembled_prompt", "")
            if "{{" not in assembled:
                print("✅ assembled_prompt 已替换所有占位符")
            else:
                print("❌ assembled_prompt 仍有未替换的占位符")
            
            if "[用户对话内容将在这里插入]" in assembled:
                print("✅ assembled_prompt 包含示例查询占位符")
            
            print("\n【Prompt 长度统计】")
            print(f"  template_base: {len(template_base)} 字符")
            print(f"  fields_instructions: {len(fields_instructions)} 字符")
            print(f"  assembled_prompt: {len(assembled)} 字符")


async def main():
    await verify_openai_compliance()
    await verify_prompt_completeness()
    
    print("\n" + "=" * 80)
    print("验证完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
