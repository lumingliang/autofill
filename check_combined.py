#!/usr/bin/env python3
"""检查合并接口返回的数据"""

import asyncio
import httpx
import json

API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
BASE_URL = "http://localhost:9999"


async def main():
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
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
        
        print("=" * 80)
        print("合并接口返回数据")
        print("=" * 80)
        
        combined = data.get("data", {}).get("combined_schema", {})
        
        print("\n【Function Calling Schema】")
        func = combined.get("function_calling", {})
        schema = func.get("schema", {})
        print(json.dumps(schema, indent=2, ensure_ascii=False))
        
        print("\n【验证 Schema 结构】")
        print(f"type: {schema.get('type')}")
        func_def = schema.get("function", {})
        print(f"function.name: {func_def.get('name')}")
        print(f"function.description: {func_def.get('description')}")
        params = func_def.get("parameters", {})
        print(f"parameters.type: {params.get('type')}")
        props = params.get("properties", {})
        print(f"properties 数量: {len(props)}")
        print(f"properties keys: {list(props.keys())}")
        print(f"required: {params.get('required', [])}")


if __name__ == "__main__":
    asyncio.run(main())
