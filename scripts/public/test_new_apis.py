#!/usr/bin/env python3
"""测试新接口"""

import asyncio
import httpx
import json

API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
BASE_URL = "http://localhost:9999"


async def test_field_groups_schema():
    """测试合并接口 /autofill/field_groups/schema"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        print("=" * 60)
        print("测试 1: 只传 group_names，查询 default 字段组")
        print("=" * 60)
        resp = await client.post(
            f"{BASE_URL}/api/autofill/field_groups/schema",
            headers=headers,
            json={"page_name": "用户信息页", "group_names": ["default"]}
        )
        data = resp.json().get("data", {})
        fields = data.get('fields', [])
        print(f"字段组数量: {len(data.get('field_groups', []))}")
        print(f"字段总数: {len(fields)}")
        print(f"字段列表: {[f.get('field_name') for f in fields][:5]} ...")
        print(f"合并Schema是否存在: {data.get('combined_schema') is not None}")
        print()

        print("=" * 60)
        print("测试 2: 传 group_names + field_names，只查询指定字段")
        print("=" * 60)
        resp = await client.post(
            f"{BASE_URL}/api/autofill/field_groups/schema",
            headers=headers,
            json={
                "page_name": "用户信息页",
                "group_names": ["default"],
                "field_names": ["一级事件类型", "智能网联-二三级"]
            }
        )
        data = resp.json().get("data", {})
        fields = data.get('fields', [])
        print(f"字段组数量: {len(data.get('field_groups', []))}")
        print(f"字段总数: {len(fields)}")
        print(f"字段列表: {[f.get('field_name') for f in fields]}")
        print()

        print("=" * 60)
        print("测试 3: 只传 field_names，查询包含这些字段的字段组")
        print("=" * 60)
        resp = await client.post(
            f"{BASE_URL}/api/autofill/field_groups/schema",
            headers=headers,
            json={
                "page_name": "用户信息页",
                "field_names": ["一级事件类型"]
            }
        )
        data = resp.json().get("data", {})
        fields = data.get('fields', [])
        print(f"字段组数量: {len(data.get('field_groups', []))}")
        print(f"字段总数: {len(fields)}")
        print(f"字段列表: {[f.get('field_name') for f in fields]}")
        print()
        
        print("=" * 60)
        print("测试 4: 查看合并后的 Function Calling Schema")
        print("=" * 60)
        resp = await client.post(
            f"{BASE_URL}/api/autofill/field_groups/schema",
            headers=headers,
            json={
                "page_name": "用户信息页", 
                "group_names": ["default"],
                "field_names": ["一级事件类型", "智能网联-二三级"]
            }
        )
        data = resp.json().get("data", {})
        combined = data.get('combined_schema', {})
        func_calling = combined.get('function_calling', {})
        schema = func_calling.get('schema', {})
        # 新的 Schema 结构: type + function
        func_def = schema.get('function', {})
        params = func_def.get('parameters', {})
        print(f"Schema Type: {schema.get('type')}")
        print(f"Function Name: {func_def.get('name')}")
        print(f"Function Description: {func_def.get('description')}")
        print(f"Properties 数量: {len(params.get('properties', {}))}")
        print(f"Properties: {list(params.get('properties', {}).keys())}")
        print(f"Required: {params.get('required', [])}")
        print()


async def test_field_group():
    """测试改造后的 /autofill/field_group 接口"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        print("=" * 60)
        print("测试 5: 改造后的 field_group 接口 - 传多个 group_names")
        print("=" * 60)
        resp = await client.post(
            f"{BASE_URL}/api/autofill/field_group",
            headers=headers,
            json={
                "page_name": "用户信息页", 
                "group_names": ["default"]
            }
        )
        data = resp.json()
        print(f"返回字段组数量: {len(data.get('data', []))}")
        if data.get('data'):
            fg = data['data'][0]
            print(f"字段组名: {fg.get('group_name')}")
            print(f"字段数量: {len(fg.get('field_specs', []))}")
            print(f"Prompt 是否存在: {fg.get('prompt_info') is not None}")
            print(f"Function Calling 是否存在: {fg.get('function_calling') is not None}")
        print()


async def test_field_spec_list():
    """测试改造后的 /autofill/field_spec/list 接口"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        print("=" * 60)
        print("测试 6: 改造后的 field_spec/list 接口 - 传多个 group_names + field_names")
        print("=" * 60)
        resp = await client.post(
            f"{BASE_URL}/api/autofill/field_spec/list",
            headers=headers,
            json={
                "page_name": "用户信息页", 
                "group_names": ["default"],
                "field_names": ["一级事件类型", "智能网联-二三级", "产品咨询-二三级"]
            }
        )
        data = resp.json()
        fields = data.get('data', [])
        print(f"返回字段数量: {len(fields)}")
        for f in fields:
            print(f"  - {f.get('field_name')}")
        print()


async def main():
    print("\n" + "=" * 60)
    print("开始测试新接口")
    print("=" * 60 + "\n")
    
    await test_field_groups_schema()
    await test_field_group()
    await test_field_spec_list()
    
    print("=" * 60)
    print("所有测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
