#!/usr/bin/env python3
"""验证接口返回的 Prompt 和 Function Calling Schema 正确性"""

import asyncio
import httpx
import json

API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
BASE_URL = "http://localhost:9999"


async def verify_field_group_schema():
    """验证 /autofill/field_group 接口返回的 Schema"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        print("=" * 80)
        print("验证 /autofill/field_group 接口")
        print("=" * 80)
        
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
        
        if data.get("code") != 200:
            print(f"❌ 接口返回错误: {data}")
            return False
            
        field_groups = data.get("data", [])
        if not field_groups:
            print("❌ 未返回字段组数据")
            return False
            
        fg = field_groups[0]
        
        # 验证 prompt_info
        print("\n【Prompt Info 验证】")
        prompt_info = fg.get("prompt_info")
        if not prompt_info:
            print("❌ prompt_info 不存在")
            return False
            
        print(f"✅ template_base 存在: {bool(prompt_info.get('template_base'))}")
        print(f"✅ fields_instructions 存在: {bool(prompt_info.get('fields_instructions'))}")
        print(f"✅ assembled_prompt 存在: {bool(prompt_info.get('assembled_prompt'))}")
        
        # 验证 assembled_prompt 内容
        assembled_prompt = prompt_info.get("assembled_prompt", "")
        if "一级事件类型" not in assembled_prompt:
            print(f"❌ assembled_prompt 未包含字段信息")
            return False
        print(f"✅ assembled_prompt 包含字段信息")
        
        # 打印 assembled_prompt 前 500 字符
        print(f"\nassembled_prompt 预览:\n{assembled_prompt[:500]}...")
        
        # 验证 function_calling
        print("\n【Function Calling 验证】")
        function_calling = fg.get("function_calling")
        if not function_calling:
            print("❌ function_calling 不存在")
            return False
            
        schema = function_calling.get("schema")
        if not schema:
            print("❌ schema 不存在")
            return False
            
        print(f"✅ schema 存在")
        print(f"✅ json_schema 存在: {bool(function_calling.get('json_schema'))}")
        
        # 验证 schema 结构
        func = schema.get("function", {})
        print(f"\nFunction Name: {func.get('name')}")
        print(f"Function Description: {func.get('description')}")
        
        params = func.get("parameters", {})
        properties = params.get("properties", {})
        print(f"Properties 数量: {len(properties)}")
        print(f"Properties Keys: {list(properties.keys())}")
        
        # 验证每个字段的 schema
        for field_name, field_schema in properties.items():
            print(f"\n  字段 '{field_name}':")
            print(f"    - type: {field_schema.get('type')}")
            print(f"    - description: {field_schema.get('description', '')[:50]}...")
            if "enum" in field_schema:
                print(f"    - enum 数量: {len(field_schema['enum'])}")
                print(f"    - enum 前3项: {field_schema['enum'][:3]}")
        
        return True


async def verify_combined_schema():
    """验证合并接口返回的 combined_schema"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        print("\n" + "=" * 80)
        print("验证 /autofill/field_groups/schema 合并接口")
        print("=" * 80)
        
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
        
        if data.get("code") != 200:
            print(f"❌ 接口返回错误: {data}")
            return False
            
        result = data.get("data", {})
        
        # 验证 fields_summary
        print("\n【Fields Summary 验证】")
        fields_summary = result.get("fields_summary")
        if not fields_summary:
            print("❌ fields_summary 不存在")
            return False
        print(f"✅ total_fields: {fields_summary.get('total_fields')}")
        print(f"✅ field_names: {fields_summary.get('field_names')}")
        
        # 验证 combined_schema
        print("\n【Combined Schema 验证】")
        combined = result.get("combined_schema")
        if not combined:
            print("❌ combined_schema 不存在")
            return False
        print(f"✅ combined_schema 存在")
        
        # 验证 combined prompt_info
        prompt_info = combined.get("prompt_info")
        if not prompt_info:
            print("❌ combined_schema.prompt_info 不存在")
            return False
        print(f"✅ combined_schema.prompt_info 存在")
        
        # 验证 assembled_prompt 包含所有字段
        assembled_prompt = prompt_info.get("assembled_prompt", "")
        required_fields = ["一级事件类型", "智能网联-二三级"]
        for field in required_fields:
            if field not in assembled_prompt:
                print(f"❌ assembled_prompt 未包含字段: {field}")
                return False
        print(f"✅ assembled_prompt 包含所有字段: {required_fields}")
        
        # 打印 assembled_prompt
        print(f"\ncombined assembled_prompt 预览:\n{assembled_prompt[:800]}...")
        
        # 验证 combined function_calling
        print("\n【Combined Function Calling 验证】")
        func_calling = combined.get("function_calling")
        if not func_calling:
            print("❌ combined_schema.function_calling 不存在")
            return False
        print(f"✅ combined_schema.function_calling 存在")
        
        schema = func_calling.get("schema", {})
        print(f"\nCombined Function Name: {schema.get('name')}")
        print(f"Combined Function Description: {schema.get('description')}")
        
        params = schema.get("parameters", {})
        properties = params.get("properties", {})
        print(f"Combined Properties 数量: {len(properties)}")
        print(f"Combined Properties Keys: {list(properties.keys())}")
        
        # 验证是否包含所有字段
        for field in required_fields:
            if field not in properties:
                print(f"❌ combined schema 未包含字段: {field}")
                return False
        print(f"✅ combined schema 包含所有字段: {required_fields}")
        
        # 验证每个字段的 schema 完整性
        for field_name, field_schema in properties.items():
            print(f"\n  字段 '{field_name}':")
            print(f"    - type: {field_schema.get('type')}")
            print(f"    - description: {field_schema.get('description', '')[:50]}...")
            if "enum" in field_schema:
                enum_values = field_schema['enum']
                print(f"    - enum 数量: {len(enum_values)}")
                print(f"    - enum 类型检查: 都是字符串: {all(isinstance(v, str) for v in enum_values)}")
        
        # 验证 json_schema 字符串
        json_schema_str = func_calling.get("json_schema")
        if not json_schema_str:
            print("❌ json_schema 字符串不存在")
            return False
        try:
            parsed = json.loads(json_schema_str)
            print(f"\n✅ json_schema 是可解析的 JSON")
            print(f"✅ 解析后的 properties 数量: {len(parsed.get('parameters', {}).get('properties', {}))}")
        except json.JSONDecodeError as e:
            print(f"❌ json_schema 解析失败: {e}")
            return False
        
        return True


async def verify_field_spec_list():
    """验证 /autofill/field_spec/list 接口"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        print("\n" + "=" * 80)
        print("验证 /autofill/field_spec/list 接口")
        print("=" * 80)
        
        resp = await client.post(
            f"{BASE_URL}/api/autofill/field_spec/list",
            headers=headers,
            json={
                "page_name": "用户信息页",
                "group_names": ["default"],
                "field_names": ["一级事件类型"]
            }
        )
        data = resp.json()
        
        if data.get("code") != 200:
            print(f"❌ 接口返回错误: {data}")
            return False
            
        fields = data.get("data", [])
        print(f"✅ 返回字段数量: {len(fields)}")
        
        if not fields:
            print("❌ 未返回字段数据")
            return False
            
        field = fields[0]
        print(f"\n字段详情:")
        print(f"  - id: {field.get('id')}")
        print(f"  - field_name: {field.get('field_name')}")
        print(f"  - field_label: {field.get('field_label')}")
        print(f"  - field_type: {field.get('field_type')}")
        print(f"  - fill_instruction: {field.get('fill_instruction', '')[:50]}...")
        
        # 验证 options
        options = field.get("options")
        if options:
            items = options.get("items", [])
            print(f"  - options.items 数量: {len(items)}")
            if items:
                print(f"  - 第一个选项: {items[0]}")
        
        return True


async def main():
    print("\n" + "=" * 80)
    print("开始验证接口返回数据的正确性")
    print("=" * 80 + "\n")
    
    results = []
    
    results.append(("field_group", await verify_field_group_schema()))
    results.append(("field_groups/schema", await verify_combined_schema()))
    results.append(("field_spec/list", await verify_field_spec_list()))
    
    print("\n" + "=" * 80)
    print("验证结果汇总")
    print("=" * 80)
    
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ 所有验证通过！接口返回数据正确。")
    else:
        print("❌ 部分验证失败，需要修复。")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
