#!/usr/bin/env python3
"""测试重构后的接口"""

import asyncio
import httpx
import json

API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
BASE_URL = "http://localhost:9999"


async def test_case(client, headers, name, payload):
    """测试单个用例"""
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"{'='*60}")
    
    resp = await client.post(
        f"{BASE_URL}/api/autofill/field_groups/schema",
        headers=headers,
        json=payload
    )
    data = resp.json().get("data", {})
    
    fields = data.get("fields", [])
    merged_config = data.get("merged_config", {})
    prompt_info = data.get("prompt_info", {})
    function_calling = data.get("function_calling", {})
    
    print(f"字段数量: {len(fields)}")
    if fields:
        print(f"字段列表: {[f.get('field_name') for f in fields][:5]}...")
    
    print(f"merged_config.prompt_template_base: {bool(merged_config.get('prompt_template_base'))}")
    print(f"merged_config.output_templates: {len(merged_config.get('output_templates', {}))} 个模板")
    
    print(f"prompt_info.template_base: {bool(prompt_info.get('template_base'))}")
    print(f"prompt_info.fields_instructions: {len(prompt_info.get('fields_instructions', ''))} 字符")
    print(f"prompt_info.assembled_prompt: {len(prompt_info.get('assembled_prompt', ''))} 字符")
    
    schema = function_calling.get("schema", {})
    func_def = schema.get("function", {})
    params = func_def.get("parameters", {})
    print(f"function_calling.schema.type: {schema.get('type')}")
    print(f"function_calling.schema.function.name: {func_def.get('name')}")
    print(f"function_calling.schema.function.parameters.properties: {len(params.get('properties', {}))} 个字段")
    print(f"function_calling.json_schema: {bool(function_calling.get('json_schema'))}")
    
    return data


async def main():
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        # 测试1: 不传 group_names，使用 default
        await test_case(
            client, headers,
            "不传 group_names，使用 default",
            {"page_name": "用户信息页"}
        )
        
        # 测试2: 传 group_names
        await test_case(
            client, headers,
            "传 group_names = ['default']",
            {"page_name": "用户信息页", "group_names": ["default"]}
        )
        
        # 测试3: 传 group_names + field_names 过滤
        await test_case(
            client, headers,
            "传 group_names + field_names 过滤",
            {
                "page_name": "用户信息页",
                "group_names": ["default"],
                "field_names": ["一级事件类型", "智能网联-二三级"]
            }
        )
        
        # 测试4: 只传 field_names（不传 group_names，用 default）
        await test_case(
            client, headers,
            "只传 field_names（不传 group_names）",
            {
                "page_name": "用户信息页",
                "field_names": ["一级事件类型"]
            }
        )
        
        # 测试5: 查看完整的 Function Schema 结构
        print(f"\n{'='*60}")
        print("测试: 查看完整的 Function Schema 结构")
        print(f"{'='*60}")
        resp = await client.post(
            f"{BASE_URL}/api/autofill/field_groups/schema",
            headers=headers,
            json={
                "page_name": "用户信息页",
                "field_names": ["一级事件类型"]
            }
        )
        data = resp.json().get("data", {})
        schema = data.get("function_calling", {}).get("schema", {})
        print(json.dumps(schema, indent=2, ensure_ascii=False))
        
        print(f"\n{'='*60}")
        print("所有测试完成!")
        print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
